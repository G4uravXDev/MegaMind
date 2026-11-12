"""Tests for MegaMindApp and widgets."""

from __future__ import annotations

import pytest
from megamind.app import MegaMindApp
from megamind.screens.dashboard import DashboardScreen
from megamind.widgets.confirm_dialog import ConfirmDialog


@pytest.mark.anyio
async def test_megamind_app_mount(repo_with_commits) -> None:
    app = MegaMindApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
            assert app.screen.query_one("#dashboard-files") is not None
            assert app.screen.query_one("#dashboard-commits") is not None
            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_confirm_dialog_cancel(repo_with_commits) -> None:
    app = MegaMindApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            dialog = ConfirmDialog(
                "Test Delete", "Are you sure?", "file.txt will be lost"
            )
            app.push_screen(dialog)
            await pilot.pause()
            assert isinstance(app.screen, ConfirmDialog)
            # Press escape to cancel
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmDialog)
            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()
