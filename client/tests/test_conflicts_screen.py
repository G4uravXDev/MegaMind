"""Tests for Milestone 7: Merge conflict resolution screen."""

from __future__ import annotations

import os

import git
import pytest

from zit.app import ZitApp
from zit.screens.conflicts import ConflictResolutionScreen
from zit.screens.dashboard import DashboardScreen
from zit.services.git_service import GitService


def test_conflicted_repo_fixture(conflicted_repo: git.Repo) -> None:
    """Verifies that conflicted_repo fixture contains active merge conflicts."""
    gs = GitService(conflicted_repo.working_dir)
    try:
        health = gs.get_repo_health()
        assert health.has_conflicts
        conflicted = gs.get_conflicted_files()
        assert "conflict.txt" in conflicted
    finally:
        gs.close()


@pytest.mark.anyio
async def test_navigate_to_conflicts(conflicted_repo: git.Repo) -> None:
    """Pressing 'm' on dashboard with conflicts navigates to ConflictResolutionScreen."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=conflicted_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            await pilot.press("m")
            await pilot.pause()
            assert isinstance(app.screen, ConflictResolutionScreen)

            # Check status labels
            from textual.widgets import Label

            title = app.screen.query_one("#conflict-title", Label)
            assert "conflict.txt" in str(title.render())
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_conflict_screen_panels_display(conflicted_repo: git.Repo) -> None:
    """Three panels display ours, AI editable center, and theirs content."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=conflicted_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, ConflictResolutionScreen)

            from textual.widgets import Static, TextArea

            ours = screen.query_one("#conflict-ours-content", Static)
            theirs = screen.query_one("#conflict-theirs-content", Static)
            center = screen.query_one("#conflict-resolution-input", TextArea)

            assert "ours change on main" in str(ours.render())
            assert "theirs change on feature" in str(theirs.render())
            assert "ours change on main" in center.text
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_ai_resolve_and_apply_flow(conflicted_repo: git.Repo) -> None:
    """Requesting AI resolution and applying resolves and stages the file."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=conflicted_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, ConflictResolutionScreen)

            from textual.widgets import TextArea

            center = screen.query_one("#conflict-resolution-input", TextArea)

            # Request AI resolution (calls mock resolve_conflict in worker)
            screen.action_request_ai_resolution()
            for _ in range(5):
                await pilot.pause()
                if "Resolved by ZIT Mock" in center.text:
                    break

            # Verify mock resolution was received and loaded
            assert "Resolved by ZIT Mock" in center.text

            # Apply hunk suggestion
            screen.action_apply_hunk_suggestion()
            await pilot.pause()

            # The file should now be resolved and staged
            gs = GitService(conflicted_repo.working_dir)
            try:
                conflicted_after = gs.get_conflicted_files()
                assert len(conflicted_after) == 0

                staged = gs.get_staged_files()
                assert "conflict.txt" in staged
            finally:
                gs.close()

            # Screen should show clean state
            from textual.widgets import Label

            title = screen.query_one("#conflict-title", Label)
            assert "No Conflicts" in str(title.render())
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_clean_repo_conflicts_screen(repo_with_commits: git.Repo) -> None:
    """Opening ConflictResolutionScreen on clean repo shows clean state safely."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            # Push conflict screen directly
            app.push_screen(ConflictResolutionScreen())
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, ConflictResolutionScreen)

            from textual.widgets import Label

            title = screen.query_one("#conflict-title", Label)
            assert "No Conflicts" in str(title.render())
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_conflicts_escape_returns_to_dashboard(
    conflicted_repo: git.Repo,
) -> None:
    """Pressing Esc returns from conflicts screen to dashboard."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=conflicted_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()
            assert isinstance(app.screen, ConflictResolutionScreen)

            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
    finally:
        del os.environ["ZIT_MOCK"]
