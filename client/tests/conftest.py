"""Shared pytest fixtures for MEGAMIND client tests."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from collections.abc import Generator
from pathlib import Path

import git
import pytest


def _remove_readonly(func, path, excinfo):
    """Handles read-only files during rmtree on Windows."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    td = tempfile.mkdtemp()
    try:
        yield Path(td)
    finally:
        shutil.rmtree(td, onerror=_remove_readonly)


@pytest.fixture
def empty_repo(temp_dir: Path) -> Generator[git.Repo, None, None]:
    """Creates a blank git repo with zero commits."""
    repo = git.Repo.init(temp_dir)
    try:
        yield repo
    finally:
        repo.close()


@pytest.fixture
def repo_with_commits(temp_dir: Path) -> Generator[git.Repo, None, None]:
    """Creates a git repo with initial commits and multiple branches."""
    repo = git.Repo.init(temp_dir)
    try:
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        file_a = temp_dir / "file_a.txt"
        file_a.write_text("initial content\n")
        repo.index.add(["file_a.txt"])
        repo.index.commit("Initial commit")

        file_b = temp_dir / "file_b.txt"
        file_b.write_text("feature content\n")
        repo.index.add(["file_b.txt"])
        repo.index.commit("Add file_b")

        yield repo
    finally:
        repo.close()


@pytest.fixture
def dirty_repo(
    repo_with_commits: git.Repo, temp_dir: Path
) -> Generator[git.Repo, None, None]:
    """Creates a repo with staged, unstaged, and untracked changes."""
    # Staged change
    staged_file = temp_dir / "staged.txt"
    staged_file.write_text("staged content\n")
    repo_with_commits.index.add(["staged.txt"])

    # Unstaged change
    file_a = temp_dir / "file_a.txt"
    file_a.write_text("modified content\n")

    # Untracked change
    untracked_file = temp_dir / "untracked.txt"
    untracked_file.write_text("untracked content\n")

    yield repo_with_commits


@pytest.fixture
def conflicted_repo(temp_dir: Path) -> Generator[git.Repo, None, None]:
    """Creates a git repository in an active merge conflict state."""
    repo = git.Repo.init(temp_dir)
    try:
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Initial common commit
        initial_branch = repo.active_branch.name
        cfile = temp_dir / "conflict.txt"
        cfile.write_text("common header\ncommon base\n")
        repo.index.add(["conflict.txt"])
        repo.index.commit("Base commit")

        # Create feature branch
        feat_branch = repo.create_head("feature-branch")

        # Commit on current branch (main)
        cfile.write_text("common header\nours change on main\n")
        repo.index.add(["conflict.txt"])
        repo.index.commit("Commit on main")

        # Checkout feature branch and commit conflicting change
        feat_branch.checkout()
        cfile.write_text("common header\ntheirs change on feature\n")
        repo.index.add(["conflict.txt"])
        repo.index.commit("Commit on feature")

        # Switch back to initial branch and merge feature-branch (triggers conflict)
        repo.git.checkout(initial_branch)
        try:
            repo.git.merge("feature-branch")
        except git.GitCommandError:
            pass

        yield repo
    finally:
        repo.close()
