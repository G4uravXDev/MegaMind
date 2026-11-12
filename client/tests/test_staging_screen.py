"""Tests for StagingScreen."""

from __future__ import annotations

from pathlib import Path

import git
import pytest
from megamind.app import MegaMindApp
from megamind.screens.dashboard import DashboardScreen
from megamind.screens.staging import StagingScreen
from megamind.widgets.confirm_dialog import ConfirmDialog


@pytest.mark.anyio
async def test_navigate_to_staging(dirty_repo: git.Repo) -> None:
    app = MegaMindApp(repo_path=dirty_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            # Press 's' to go to staging
            await pilot.press("s")
            await pilot.pause()
            assert isinstance(app.screen, StagingScreen)

            # Press 'escape' to go back to dashboard
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_staging_toggle_and_actions(dirty_repo: git.Repo) -> None:
    app = MegaMindApp(repo_path=dirty_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            staging = app.screen
            assert isinstance(staging, StagingScreen)

            # Stage all changes with 'a'
            await pilot.press("a")
            await pilot.pause()
            status = app.git_service.get_status_entries()
            assert len(status["staged"]) >= 2
            assert len(status["unstaged"]) == 0

            # Unstage all changes with 'u'
            await pilot.press("u")
            await pilot.pause()
            status = app.git_service.get_status_entries()
            assert len(status["staged"]) == 0

            # Toggle stage on the currently highlighted file
            await pilot.press("enter")
            await pilot.pause()
            status = app.git_service.get_status_entries()
            assert len(status["staged"]) >= 1

            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_staging_discard_dialog(dirty_repo: git.Repo, temp_dir: Path) -> None:
    app = MegaMindApp(repo_path=dirty_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            staging = app.screen
            assert isinstance(staging, StagingScreen)

            # Unstage all first so files are unstaged/untracked
            await pilot.press("u")
            await pilot.pause()

            # Press 'd' to open discard confirm dialog
            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmDialog)

            # Cancel discard dialog with Escape
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, StagingScreen)

            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()
