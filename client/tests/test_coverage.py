"""Tests for Milestone 9: AI test coverage generation and save."""

from __future__ import annotations

import os
from pathlib import Path

import git
import pytest
from megamind.app import MegaMindApp
from megamind.screens.dashboard import DashboardScreen
from megamind.screens.staging import StagingScreen
from megamind.widgets.coverage_modal import CoverageModal
from megamind.widgets.file_list import FileList
from megamind.widgets.input_dialog import InputDialog


@pytest.mark.anyio
async def test_coverage_modal_direct_save(temp_dir: Path) -> None:
    """CoverageModal renders generated code and saves to chosen filename."""
    app = MegaMindApp(repo_path=temp_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()

            test_code = "import pytest\n\ndef test_hello():\n    assert True\n"
            modal = CoverageModal("hello.py", test_code)
            app.push_screen(modal)
            await pilot.pause()

            assert isinstance(app.screen, CoverageModal)

            from textual.widgets import TextArea

            view = app.screen.query_one("#coverage-code-view", TextArea)
            assert "test_hello" in view.text

            # Trigger save
            modal.action_save_file()
            await pilot.pause()

            # InputDialog should be open
            assert isinstance(app.screen, InputDialog)

            # Submit a custom filename
            app.screen._submit("tests/test_custom.py")
            await pilot.pause()

            # Verify file was written to disk
            saved_file = temp_dir / "tests" / "test_custom.py"
            assert saved_file.exists()
            assert "test_hello" in saved_file.read_text(encoding="utf-8")
    finally:
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_coverage_from_dashboard(dirty_repo: git.Repo) -> None:
    """Pressing 'v' on dashboard file generates coverage and pushes CoverageModal."""
    os.environ["MEGAMIND_MOCK"] = "1"
    app = MegaMindApp(repo_path=dirty_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            # Highlight a file in the dashboard file list
            file_list = app.screen.query_one("#dashboard-files", FileList)
            file_list.focus()
            await pilot.pause()

            # Press 'v' to generate coverage
            await pilot.press("v")

            # Wait for background worker to complete
            for _ in range(5):
                await pilot.pause()
                if isinstance(app.screen, CoverageModal):
                    break

            assert isinstance(app.screen, CoverageModal)
            from textual.widgets import TextArea

            view = app.screen.query_one("#coverage-code-view", TextArea)
            assert "Generated test suite" in view.text

            # Press Escape to close modal
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
    finally:
        del os.environ["MEGAMIND_MOCK"]
        if app._git_service:
            app._git_service.close()


@pytest.mark.anyio
async def test_coverage_from_staging(dirty_repo: git.Repo) -> None:
    """Pressing 'v' in staging generates coverage for the highlighted file."""
    os.environ["MEGAMIND_MOCK"] = "1"
    app = MegaMindApp(repo_path=dirty_repo.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            assert isinstance(app.screen, StagingScreen)

            # Trigger coverage
            await pilot.press("v")

            # Wait for background worker
            for _ in range(5):
                await pilot.pause()
                if isinstance(app.screen, CoverageModal):
                    break

            assert isinstance(app.screen, CoverageModal)
            from textual.widgets import TextArea

            view = app.screen.query_one("#coverage-code-view", TextArea)
            assert "Generated test suite" in view.text
    finally:
        del os.environ["MEGAMIND_MOCK"]
        if app._git_service:
            app._git_service.close()
