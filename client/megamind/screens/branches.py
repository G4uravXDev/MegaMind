"""Branches screen for listing, creating, renaming, switching, and deleting branches."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, OptionList
from textual.widgets.option_list import Option

from megamind.services.exceptions import DestructiveActionError, GitServiceError
from megamind.services.git_service import BranchInfo
from megamind.widgets.confirm_dialog import ConfirmDialog
from megamind.widgets.error_panel import ErrorModal
from megamind.widgets.input_dialog import InputDialog
from megamind.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from megamind.app import MegaMindApp


class BranchesScreen(Screen[None]):
    """Screen for managing local git branches."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_to_dashboard", "Dashboard"),
        Binding("enter", "switch_branch", "Switch"),
        Binding("n", "create_branch", "New Branch"),
        Binding("r", "rename_branch", "Rename"),
        Binding("d", "delete_branch", "Delete"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._branches: list[BranchInfo] = []

    @property
    def megamind_app(self) -> MegaMindApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label("🌿 BRANCHES", classes="status-badge badge-branch")
            yield Label(
                "Enter: Switch  |  n: Create  |  r: Rename  |  d: Delete",
                classes="status-badge",
            )
        with Vertical(id="branches-main"):
            yield Label("🌿 Local Branches", classes="panel-header")
            yield OptionList(id="branch-options")
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_branches()

    def refresh_branches(self) -> None:
        """Fetches all local branches and updates the list."""
        try:
            git_service = self.megamind_app.git_service
            self._branches = git_service.get_branches()

            option_list = self.query_one("#branch-options", OptionList)
            prev_idx = option_list.highlighted or 0
            option_list.clear_options()

            if not self._branches:
                empty = Text("  (No local branches found)", style="dim italic")
                option_list.add_option(Option(empty, disabled=True))
                return

            options: list[Option] = []
            current_idx = 0
            for idx, b in enumerate(self._branches):
                label = Text()
                if b.is_current:
                    current_idx = idx
                    label.append(" ● [ACTIVE] ", style="bold green")
                    label.append(f"{b.name:25s} ", style="bold green")
                else:
                    label.append(" ○ [LOCAL]  ", style="dim cyan")
                    label.append(f"{b.name:25s} ", style="bold white")

                if b.commit_hash:
                    label.append(f"{b.commit_hash} ", style="yellow")
                    label.append(f"- {b.commit_message[:45]}", style="dim")
                options.append(Option(label, id=b.name))

            option_list.add_options(options)
            # Default highlight to previously selected index or current branch
            target_idx = prev_idx if prev_idx < len(options) else current_idx
            option_list.highlighted = target_idx

        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Git Error", str(err)))
        except Exception as err:  # noqa: BLE001
            self.app.push_screen(ErrorModal("Unexpected Error", str(err)))

    def _get_highlighted_branch(self) -> BranchInfo | None:
        """Returns the currently highlighted branch."""
        option_list = self.query_one("#branch-options", OptionList)
        idx = option_list.highlighted
        if idx is not None and 0 <= idx < len(self._branches):
            return self._branches[idx]
        return None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.action_switch_branch()

    def action_switch_branch(self) -> None:
        """Switches to the selected branch."""
        branch = self._get_highlighted_branch()
        if not branch:
            return

        if branch.is_current:
            self.notify(f"Already on branch '{branch.name}'.", severity="information")
            return

        try:
            self.megamind_app.git_service.switch_branch(branch.name)
            self.notify(
                f"Switched to branch '{branch.name}'",
                title="Branch Switch",
                severity="information",
            )
            self.refresh_branches()
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Cannot Switch Branch", str(err)))

    def action_create_branch(self) -> None:
        """Prompts for a new branch name and creates it."""

        def on_name_entered(name: str | None) -> None:
            if not name:
                return
            try:
                self.megamind_app.git_service.create_branch(name)
                self.notify(
                    f"Created branch '{name}'",
                    title="Git Branch",
                    severity="information",
                )
                self.refresh_branches()
            except GitServiceError as err:
                self.app.push_screen(ErrorModal("Create Branch Failed", str(err)))

        dialog = InputDialog(
            title="Create New Branch",
            prompt="Enter name for new branch:",
            placeholder="feature/my-branch",
            confirm_label="Create",
        )
        self.app.push_screen(dialog, on_name_entered)

    def action_rename_branch(self) -> None:
        """Prompts to rename the selected branch."""
        branch = self._get_highlighted_branch()
        if not branch:
            self.notify("Select a branch to rename.", severity="warning")
            return

        def on_name_entered(new_name: str | None) -> None:
            if not new_name or new_name == branch.name:
                return
            try:
                self.megamind_app.git_service.rename_branch(branch.name, new_name)
                self.notify(
                    f"Renamed '{branch.name}' to '{new_name}'",
                    title="Git Branch",
                    severity="information",
                )
                self.refresh_branches()
            except GitServiceError as err:
                self.app.push_screen(ErrorModal("Rename Branch Failed", str(err)))

        dialog = InputDialog(
            title=f"Rename Branch '{branch.name}'",
            prompt=f"Enter new name for branch '{branch.name}':",
            initial_value=branch.name,
            confirm_label="Rename",
        )
        self.app.push_screen(dialog, on_name_entered)

    def action_delete_branch(self) -> None:
        """Deletes selected branch after confirmation."""
        branch = self._get_highlighted_branch()
        if not branch:
            self.notify("Select a branch to delete.", severity="warning")
            return

        if branch.is_current:
            self.notify(
                f"Cannot delete branch '{branch.name}' because it is currently checked out. "
                "Switch to another branch first.",
                severity="error",
                title="Delete Refused",
            )
            return

        def on_confirmed(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                self.megamind_app.git_service.delete_branch(branch.name, force=True)
                self.notify(
                    f"Deleted branch '{branch.name}'",
                    title="Git Branch",
                    severity="information",
                )
                self.refresh_branches()
            except (DestructiveActionError, GitServiceError) as err:
                self.app.push_screen(ErrorModal("Delete Branch Failed", str(err)))

        dialog = ConfirmDialog(
            title="Delete Branch",
            message=f"Are you sure you want to delete branch '{branch.name}'?",
            details=f"Branch '{branch.name}' and any unmerged commits specific to it will be permanently deleted.",
            confirm_label="Delete Branch",
        )
        self.app.push_screen(dialog, on_confirmed)

    def action_back_to_dashboard(self) -> None:
        self.megamind_app.action_back_to_dashboard()

    def action_quit_app(self) -> None:
        self.app.exit()
