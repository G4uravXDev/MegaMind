"""Staging screen for staging and unstaging files with diff preview."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label

from zit.services.exceptions import GitServiceError
from zit.widgets.confirm_dialog import ConfirmDialog
from zit.widgets.diff_view import DiffView
from zit.widgets.error_panel import ErrorModal
from zit.widgets.file_list import FileItem, FileList
from zit.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from zit.app import ZitApp


class StagingScreen(Screen[None]):
    """Interactive staging manager with live diff preview."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_to_dashboard", "Dashboard"),
        Binding("enter", "toggle_stage", "Toggle Stage"),
        Binding("space", "toggle_stage", "Toggle Stage", show=False),
        Binding("a", "stage_all", "Stage All"),
        Binding("u", "unstage_all", "Unstage All"),
        Binding("d", "discard_file", "Discard"),
        Binding("c", "goto_commit", "Commit"),
        Binding("v", "coverage", "Coverage"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_file: FileItem | None = None

    @property
    def zit_app(self) -> ZitApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label("⚡ STAGING WORKSPACE", classes="status-badge badge-branch")
            yield Label(
                "Enter/Space: Toggle  |  a: Stage All  |  u: Unstage All  |  d: Discard",
                classes="status-badge",
            )
        with Horizontal(id="staging-main"):
            with Vertical(id="staging-left"):
                yield Label("📂 Changed Files", classes="panel-header")
                yield FileList(id="staging-file-list")
            with Vertical(id="staging-right"):
                yield Label("🔍 Diff Preview", classes="panel-header", id="diff-header")
                yield DiffView(id="staging-diff-preview")
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_staging()

    def refresh_staging(self, keep_selection: str | None = None) -> None:
        """Fetches status and updates file list and diff preview."""
        try:
            git_service = self.zit_app.git_service
            status = git_service.get_status_entries()

            file_list = self.query_one("#staging-file-list", FileList)
            file_list.set_files(
                staged=status["staged"],
                unstaged=status["unstaged"],
                untracked=status["untracked"],
                conflicted=status["conflicted"],
            )

            # Update selected item
            selected = file_list.get_selected_item()
            self._update_preview(selected)

        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Git Error", str(err)))
        except Exception as err:  # noqa: BLE001
            self.app.push_screen(ErrorModal("Unexpected Error", str(err)))

    def _update_preview(self, item: FileItem | None) -> None:
        """Updates the diff viewer for the selected file."""
        self._current_file = item
        diff_view = self.query_one("#staging-diff-preview", DiffView)
        diff_header = self.query_one("#diff-header", Label)

        if not item:
            diff_header.update("🔍 Diff Preview: (No file selected)")
            diff_view.update_diff("")
            return

        diff_header.update(f"🔍 Diff Preview: {item.path} [{item.category.upper()}]")
        git_service = self.zit_app.git_service
        try:
            if item.category == "staged":
                diff = git_service.get_staged_diff(item.path)
            else:
                diff = git_service.get_diff(item.path)
            diff_view.update_diff(diff)
        except Exception as err:  # noqa: BLE001
            diff_view.update_diff(f"Unable to generate diff: {err}")

    def on_file_list_file_highlighted(self, event: FileList.FileHighlighted) -> None:
        self._update_preview(FileItem(path=event.file_path, category=event.category))

    def on_file_list_file_selected(self, event: FileList.FileSelected) -> None:
        self._toggle_file(event.file_path, event.category)

    def action_toggle_stage(self) -> None:
        file_list = self.query_one("#staging-file-list", FileList)
        item = file_list.get_selected_item()
        if item:
            self._toggle_file(item.path, item.category)

    def _toggle_file(self, file_path: str, category: str) -> None:
        """Toggles a file between staged and unstaged/untracked."""
        git_service = self.zit_app.git_service
        try:
            if category == "staged":
                git_service.unstage_file(file_path)
                self.notify(f"Unstaged {file_path}", title="Staging")
            else:
                git_service.stage_file(file_path)
                self.notify(f"Staged {file_path}", title="Staging")
            self.refresh_staging()
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Staging Error", str(err)))

    def action_stage_all(self) -> None:
        try:
            self.zit_app.git_service.stage_all()
            self.notify("Staged all changes", title="Staging")
            self.refresh_staging()
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Stage All Error", str(err)))

    def action_unstage_all(self) -> None:
        try:
            self.zit_app.git_service.unstage_all()
            self.notify("Unstaged all changes", title="Staging")
            self.refresh_staging()
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Unstage All Error", str(err)))

    def action_discard_file(self) -> None:
        file_list = self.query_one("#staging-file-list", FileList)
        item = file_list.get_selected_item()
        if not item:
            self.notify("No file selected to discard.", severity="warning")
            return

        if item.category == "staged":
            self.notify(
                f"File '{item.path}' is staged. Unstage it before discarding.",
                severity="warning",
            )
            return

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                try:
                    self.zit_app.git_service.discard_file_changes(item.path)
                    self.notify(f"Discarded changes in {item.path}", title="Git")
                    self.refresh_staging()
                except GitServiceError as err:
                    self.app.push_screen(ErrorModal("Discard Error", str(err)))

        dialog = ConfirmDialog(
            title="Discard File Changes",
            message=f"Discard all uncommitted changes in '{item.path}'?",
            details=f"All modifications in '{item.path}' will be permanently deleted and cannot be undone.",
            confirm_label="Discard Changes",
        )
        self.app.push_screen(dialog, handle_confirm)

    def action_goto_commit(self) -> None:
        self.zit_app.show_screen("commit")

    def action_coverage(self) -> None:
        if self._current_file:
            self.zit_app.generate_coverage_for_file(self._current_file.path)
        else:
            self.notify("Select a file to generate test coverage.", severity="warning")

    def action_refresh_data(self) -> None:
        self.refresh_staging()
        self.notify("Staging refreshed", title="ZIT")

    def action_back_to_dashboard(self) -> None:
        self.zit_app.action_back_to_dashboard()

    def action_quit_app(self) -> None:
        self.app.exit()
