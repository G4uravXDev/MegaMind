"""Tests for BranchesScreen and GitService branch operations."""

from __future__ import annotations

import git
import pytest
from megamind.app import MegaMindApp
from megamind.screens.branches import BranchesScreen
from megamind.screens.dashboard import DashboardScreen
from megamind.services.exceptions import DestructiveActionError, GitServiceError
from megamind.widgets.confirm_dialog import ConfirmDialog


@pytest.mark.anyio
async def test_navigate_to_branches(repo_with_commits: git.Repo) -> None:
    app = MegaMindApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            # Press 'b' to navigate to Branches screen
            await pilot.press("b")
            await pilot.pause()
            assert isinstance(app.screen, BranchesScreen)

            # Press 'escape' to return to dashboard
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()


def test_git_service_branch_operations(repo_with_commits: git.Repo) -> None:
    service = repo_with_commits  # underlying repo
    from megamind.services.git_service import GitService

    git_service = GitService(service.working_dir)
    try:
        # Initial branch name
        initial_branch = git_service.get_current_branch()
        branches = git_service.get_branches()
        assert len(branches) == 1
        assert branches[0].is_current

        # Create branch
        git_service.create_branch("feature-1")
        branches = git_service.get_branches()
        branch_names = [b.name for b in branches]
        assert "feature-1" in branch_names

        # Switch to feature-1
        git_service.switch_branch("feature-1")
        assert git_service.get_current_branch() == "feature-1"

        # Rename feature-1 to feature-renamed
        git_service.rename_branch("feature-1", "feature-renamed")
        assert git_service.get_current_branch() == "feature-renamed"

        # Refuse to delete current branch
        with pytest.raises(DestructiveActionError):
            git_service.delete_branch("feature-renamed")

        # Switch back to master/main
        git_service.switch_branch(initial_branch)
        assert git_service.get_current_branch() == initial_branch

        # Delete feature-renamed
        git_service.delete_branch("feature-renamed")
        branch_names_after = [b.name for b in git_service.get_branches()]
        assert "feature-renamed" not in branch_names_after

    finally:
        git_service.close()


def test_switch_conflict_handling(repo_with_commits: git.Repo) -> None:
    """Verifies clear error when switching branches with conflicting local changes."""
    from pathlib import Path

    from megamind.services.git_service import GitService

    service = GitService(repo_with_commits.working_dir)
    try:
        # Create branch-b
        service.create_branch("branch-b")
        service.switch_branch("branch-b")

        # Commit a change to file_a on branch-b
        file_a = Path(repo_with_commits.working_dir) / "file_a.txt"
        file_a.write_text("branch-b changes\n")
        service.stage_file("file_a.txt")
        service.commit("Update file_a on branch-b")

        # Switch back to initial branch
        branches = service.get_branches()
        other_branch = next(b.name for b in branches if b.name != "branch-b")
        service.switch_branch(other_branch)

        # Now make an uncommitted change to file_a in working copy
        file_a.write_text("uncommitted conflicting change\n")

        # Attempting to switch to branch-b should raise GitServiceError with clear message
        with pytest.raises(GitServiceError) as exc_info:
            service.switch_branch("branch-b")

        assert "uncommitted changes that would be overwritten" in str(exc_info.value)

    finally:
        service.close()


@pytest.mark.anyio
async def test_branches_screen_delete_confirmation(repo_with_commits: git.Repo) -> None:
    """Verifies delete confirmation dialog on BranchesScreen."""
    app = MegaMindApp(repo_path=repo_with_commits.working_dir)
    app.git_service.create_branch("to-delete")

    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            branches_screen = app.screen
            assert isinstance(branches_screen, BranchesScreen)

            # Highlight 'to-delete' branch
            option_list = branches_screen.query_one("#branch-options")
            # The second option is to-delete
            option_list.highlighted = 1
            await pilot.pause()

            # Press 'd' to delete -> ConfirmDialog should pop up
            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmDialog)

            # Cancel with Escape
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, BranchesScreen)

            await pilot.exit(None)
    finally:
        if app._git_service:
            app._git_service.close()
