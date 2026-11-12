"""Tests for LogGraphScreen and GitService log graph operations."""

from __future__ import annotations

import git
import pytest
from megamind.app import MegaMindApp
from megamind.screens.dashboard import DashboardScreen
from megamind.screens.log_graph import LogGraphScreen
from megamind.services.git_service import GitService


@pytest.mark.anyio
async def test_navigate_to_log_graph(repo_with_commits: git.Repo) -> None:
    app = MegaMindApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            # Press 'l' to navigate to Log Graph screen
            await pilot.press("l")
            await pilot.pause()
            assert isinstance(app.screen, LogGraphScreen)

            # Press 'escape' to return to dashboard
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()


def test_log_graph_service_operations(repo_with_commits: git.Repo) -> None:
    service = GitService(repo_with_commits.working_dir)
    try:
        entries = service.get_log_graph()
        assert len(entries) >= 2

        # Find entry with commit hash
        commit_entries = [e for e in entries if e.commit_hash]
        assert len(commit_entries) >= 2

        top_commit = commit_entries[0]
        assert top_commit.commit_hash is not None

        # Fetch commit details
        details = service.get_commit_details(top_commit.commit_hash)
        assert details.author == "Test User"
        assert details.message.strip() == "Add file_b"
        assert len(details.files) >= 1
        assert details.files[0].path == "file_b.txt"
        assert details.total_insertions >= 1

    finally:
        service.close()


def test_log_graph_empty_repo(empty_repo: git.Repo) -> None:
    service = GitService(empty_repo.working_dir)
    try:
        entries = service.get_log_graph()
        assert entries == []
    finally:
        service.close()


@pytest.mark.anyio
async def test_log_graph_detail_view(repo_with_commits: git.Repo) -> None:
    """Verifies pressing Enter on a commit updates commit detail display."""
    app = MegaMindApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()
            log_screen = app.screen
            assert isinstance(log_screen, LogGraphScreen)

            # Press enter on the highlighted commit
            await pilot.press("enter")
            await pilot.pause()

            # Verify right panel content
            from textual.widgets import Static

            content = log_screen.query_one("#commit-detail-content", Static)
            text = str(content.render())
            assert "Commit:" in text
            assert "Author:" in text

            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()
