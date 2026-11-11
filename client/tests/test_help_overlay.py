"""Tests for Milestone 10: Help overlay modal."""

from __future__ import annotations

import os

import git
import pytest

from zit.app import ZitApp
from zit.screens.dashboard import DashboardScreen
from zit.widgets.help_overlay import HelpModal


@pytest.mark.anyio
async def test_help_modal_direct() -> None:
    """HelpModal renders quick reference text and dismisses."""
    app = ZitApp()
    try:
        async with app.run_test() as pilot:
            await pilot.pause()

            modal = HelpModal()
            app.push_screen(modal)
            await pilot.pause()

            assert isinstance(app.screen, HelpModal)
            from textual.widgets import Static

            content = app.screen.query_one("#help-scroll Static", Static)
            text = str(content.render())
            assert "Global Keybindings" in text
            assert "Staging" in text
            assert "Time Travel" in text
            assert "AI Mentor" in text

            # Dismiss
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, HelpModal)
    finally:
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_global_question_mark_shortcut(repo_with_commits: git.Repo) -> None:
    """Pressing '?' from any screen opens the HelpModal and Esc closes it."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            # Trigger help with '?'
            await pilot.press("question_mark")
            await pilot.pause()
            assert isinstance(app.screen, HelpModal)

            # Close with Esc
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
    finally:
        del os.environ["ZIT_MOCK"]
        if app._git_service:
            app._git_service.close()
