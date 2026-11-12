"""Tests for CommitScreen."""

from __future__ import annotations

import git
import pytest
from megamind.app import MegaMindApp
from megamind.screens.commit import CommitScreen
from megamind.screens.dashboard import DashboardScreen
from textual.widgets import TextArea


@pytest.mark.anyio
async def test_navigate_to_commit(dirty_repo: git.Repo) -> None:
    app = MegaMindApp(repo_path=dirty_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            # Press 'c' to navigate to Commit screen
            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, CommitScreen)

            # Press 'escape' to return to dashboard
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_commit_blocks_empty_state(repo_with_commits: git.Repo) -> None:
    """Verifies committing is blocked when nothing is staged or message is empty."""
    app = MegaMindApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            commit_screen = app.screen
            assert isinstance(commit_screen, CommitScreen)

            # Try to commit with nothing staged -> stays on CommitScreen
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert isinstance(app.screen, CommitScreen)

            # Stage a file
            app.git_service.stage_file("file_a.txt")
            commit_screen.refresh_commit_view()

            # Empty message commit -> still blocked
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert isinstance(app.screen, CommitScreen)

            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_ai_generate_and_commit(dirty_repo: git.Repo) -> None:
    """Verifies key 'g' calls AI message generation and Ctrl+S creates commit."""
    app = MegaMindApp(repo_path=dirty_repo.working_dir)
    # Ensure mock mode is active for deterministic testing
    app.api_client.mock = True

    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            commit_screen = app.screen
            assert isinstance(commit_screen, CommitScreen)

            # Press 'g' to trigger AI message generation
            await pilot.press("g")
            # Wait for background worker to populate TextArea
            for _ in range(5):
                await pilot.pause()
                text_area = commit_screen.query_one("#commit-message-input", TextArea)
                if text_area.text.strip():
                    break

            text_area = commit_screen.query_one("#commit-message-input", TextArea)
            assert "feat:" in text_area.text
            assert "MEGAMIND mock" in text_area.text

            # Now commit with Ctrl+S
            await pilot.press("ctrl+s")
            await pilot.pause()

            # Should have returned to Dashboard
            assert isinstance(app.screen, DashboardScreen)

            # Staged file should now be committed
            commits = app.git_service.get_recent_commits()
            assert "feat:" in commits[0].message

            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()
