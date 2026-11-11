"""Tests for Milestone 6: Time Travel screen – stash, reset, reflog recovery."""

from __future__ import annotations

import os

import git
import pytest

from zit.app import ZitApp
from zit.screens.dashboard import DashboardScreen
from zit.screens.time_travel import TimeTravelScreen
from zit.services.git_service import GitService

# ── GitService stash / reset / reflog unit tests ─────────────────────


def test_stash_save_and_list(repo_with_commits: git.Repo, temp_dir) -> None:
    """Save a stash and verify it appears in the list."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        # Make a dirty change
        (temp_dir / "file_a.txt").write_text("stash me\n")

        gs.stash_save("test stash entry")
        stashes = gs.stash_list()
        assert len(stashes) >= 1
        assert stashes[0].index == 0
        assert "test stash entry" in stashes[0].message
    finally:
        gs.close()


def test_stash_apply_and_drop(repo_with_commits: git.Repo, temp_dir) -> None:
    """Apply and drop stash entries."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        # Create stash
        (temp_dir / "file_a.txt").write_text("stash me\n")
        gs.stash_save("apply-test")

        # Working tree should be clean now
        health = gs.get_repo_health()
        assert health.is_clean

        # Apply without removing
        gs.stash_apply(0)
        content = (temp_dir / "file_a.txt").read_text()
        assert content == "stash me\n"

        # Stash should still exist
        stashes = gs.stash_list()
        assert len(stashes) >= 1

        # Drop the stash
        gs.stash_drop(0)
        stashes = gs.stash_list()
        assert len(stashes) == 0
    finally:
        gs.close()


def test_stash_pop(repo_with_commits: git.Repo, temp_dir) -> None:
    """Pop applies and removes the stash in one operation."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        (temp_dir / "file_a.txt").write_text("pop me\n")
        gs.stash_save("pop-test")

        gs.stash_pop(0)
        content = (temp_dir / "file_a.txt").read_text()
        assert content == "pop me\n"

        # Stash should be gone
        stashes = gs.stash_list()
        assert len(stashes) == 0
    finally:
        gs.close()


def test_stash_save_clean_tree_raises(repo_with_commits: git.Repo) -> None:
    """Saving a stash with a clean working tree should raise."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        from zit.services.exceptions import GitServiceError

        with pytest.raises(GitServiceError, match="Nothing to stash"):
            gs.stash_save("should fail")
    finally:
        gs.close()


def test_reset_soft(repo_with_commits: git.Repo) -> None:
    """Soft reset should move HEAD but keep staged changes."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        commits_before = gs.get_recent_commits(limit=5)
        assert len(commits_before) >= 2

        gs.reset("soft", "HEAD~1")

        commits_after = gs.get_recent_commits(limit=5)
        assert len(commits_after) == len(commits_before) - 1

        # Changes should be staged
        staged = gs.get_staged_files()
        assert len(staged) > 0
    finally:
        gs.close()


def test_reset_mixed(repo_with_commits: git.Repo) -> None:
    """Mixed reset should move HEAD and unstage changes."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        gs.reset("mixed", "HEAD~1")

        # Staged should be empty, unstaged or untracked should have changes
        staged = gs.get_staged_files()
        assert len(staged) == 0

        status = gs.get_status_entries()
        assert len(status["unstaged"]) > 0 or len(status["untracked"]) > 0
    finally:
        gs.close()


def test_reset_hard(repo_with_commits: git.Repo, temp_dir) -> None:
    """Hard reset should discard all changes."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        gs.reset("hard", "HEAD~1")

        commits_after = gs.get_recent_commits(limit=5)
        assert len(commits_after) == 1

        health = gs.get_repo_health()
        assert health.is_clean
    finally:
        gs.close()


def test_reset_invalid_mode(repo_with_commits: git.Repo) -> None:
    """Invalid reset mode should raise."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        from zit.services.exceptions import GitServiceError

        with pytest.raises(GitServiceError, match="Invalid reset mode"):
            gs.reset("invalid", "HEAD")
    finally:
        gs.close()


def test_reflog_entries(repo_with_commits: git.Repo) -> None:
    """Reflog should contain entries for each commit."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        entries = gs.get_reflog(limit=10)
        assert len(entries) >= 2  # At least initial + second commit
        # Each entry should have a selector
        for entry in entries:
            assert entry.selector.startswith("HEAD@{")
            assert len(entry.hash) == 7
    finally:
        gs.close()


def test_restore_to_reflog(repo_with_commits: git.Repo) -> None:
    """Restoring to a reflog entry should move HEAD."""
    gs = GitService(repo_with_commits.working_dir)
    try:
        entries = gs.get_reflog(limit=10)
        assert len(entries) >= 2

        # Get the second entry (one commit back)
        target = entries[1]
        gs.restore_to_reflog(target.selector)

        # HEAD should now match that entry's hash
        current_commits = gs.get_recent_commits(limit=1)
        assert len(current_commits) >= 1
        assert current_commits[0].hash == target.hash
    finally:
        gs.close()


# ── Screen UI tests ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_navigate_to_time_travel(repo_with_commits: git.Repo) -> None:
    """Pressing 't' on dashboard pushes TimeTravelScreen."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            await pilot.press("t")
            await pilot.pause()
            assert isinstance(app.screen, TimeTravelScreen)

            # Should show stash tab by default
            from textual.widgets import Label

            header = app.screen.query_one("#tt-panel-header", Label)
            text = str(header.render())
            assert "Stash" in text
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_time_travel_tab_switching(repo_with_commits: git.Repo) -> None:
    """Pressing 1, 2, 3 switches between tabs."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("t")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, TimeTravelScreen)

            from textual.widgets import Label

            # Switch to Reset tab
            await pilot.press("2")
            await pilot.pause()
            header = screen.query_one("#tt-panel-header", Label)
            assert "Reset" in str(header.render())

            # Switch to Recovery tab
            await pilot.press("3")
            await pilot.pause()
            header = screen.query_one("#tt-panel-header", Label)
            assert "Reflog" in str(header.render()) or "Recovery" in str(
                header.render()
            )

            # Switch back to Stash tab
            await pilot.press("1")
            await pilot.pause()
            header = screen.query_one("#tt-panel-header", Label)
            assert "Stash" in str(header.render())
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_time_travel_escape_returns_to_dashboard(
    repo_with_commits: git.Repo,
) -> None:
    """Pressing Esc on TimeTravelScreen returns to dashboard."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("t")
            await pilot.pause()
            assert isinstance(app.screen, TimeTravelScreen)

            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
    finally:
        del os.environ["ZIT_MOCK"]
