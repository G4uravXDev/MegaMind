"""Tests for GitService."""

from __future__ import annotations

from pathlib import Path

import git
import pytest

from zit.services.exceptions import GitServiceError, RepoNotFoundError
from zit.services.git_service import GitService


def test_repo_not_found(temp_dir: Path) -> None:
    non_repo = temp_dir / "not_a_repo"
    non_repo.mkdir()
    with pytest.raises(RepoNotFoundError):
        GitService(non_repo)


def test_empty_repo_handling(empty_repo: git.Repo, temp_dir: Path) -> None:
    service = GitService(temp_dir)
    assert not service.has_commits()
    assert service.get_recent_commits() == []
    branch = service.get_current_branch()
    assert branch in ("master", "main")

    health = service.get_repo_health()
    assert health.is_clean
    assert not health.has_commits
    assert health.ahead == 0
    assert health.behind == 0


def test_repo_health_and_commits(repo_with_commits: git.Repo, temp_dir: Path) -> None:
    service = GitService(temp_dir)
    assert service.has_commits()

    commits = service.get_recent_commits(limit=5)
    assert len(commits) == 2
    assert commits[0].message == "Add file_b"
    assert commits[1].message == "Initial commit"

    health = service.get_repo_health()
    assert health.is_clean
    assert health.has_commits
    assert not health.has_conflicts


def test_dirty_repo_statuses(dirty_repo: git.Repo, temp_dir: Path) -> None:
    service = GitService(temp_dir)
    status = service.get_status_entries()

    assert "staged.txt" in status["staged"]
    assert "file_a.txt" in status["unstaged"]
    assert "untracked.txt" in status["untracked"]

    health = service.get_repo_health()
    assert not health.is_clean


def test_stage_and_unstage(dirty_repo: git.Repo, temp_dir: Path) -> None:
    service = GitService(temp_dir)

    # Unstage staged.txt (it was newly added, so unstaging makes it untracked)
    service.unstage_file("staged.txt")
    assert "staged.txt" not in service.get_staged_files()
    assert "staged.txt" in service.get_untracked_files()

    # Stage it back
    service.stage_file("staged.txt")
    assert "staged.txt" in service.get_staged_files()


def test_commit_flow(repo_with_commits: git.Repo, temp_dir: Path) -> None:
    service = GitService(temp_dir)

    # Nothing staged should raise error
    with pytest.raises(GitServiceError):
        service.commit("empty")

    new_file = temp_dir / "new.txt"
    new_file.write_text("hello\n")
    service.stage_file("new.txt")

    # Empty message should raise error
    with pytest.raises(GitServiceError):
        service.commit("   ")

    service.commit("Add new.txt")
    commits = service.get_recent_commits()
    assert commits[0].message == "Add new.txt"


def test_diff_generation(dirty_repo: git.Repo, temp_dir: Path) -> None:
    service = GitService(temp_dir)
    diff = service.get_diff("file_a.txt")
    assert "-initial content" in diff
    assert "+modified content" in diff

    staged_diff = service.get_staged_diff("staged.txt")
    assert "+staged content" in staged_diff
