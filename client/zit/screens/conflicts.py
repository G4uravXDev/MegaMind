"""Merge conflict resolution screen for ZIT client."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static, TextArea

from zit.services.conflict_parser import (
    ConflictHunk,
    apply_hunk_resolution,
    parse_conflicts,
)
from zit.services.exceptions import GitServiceError
from zit.widgets.error_panel import ErrorModal
from zit.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from zit.app import ZitApp


class ConflictResolutionScreen(Screen[None]):
    """Three-panel merge conflict resolution screen with AI assistance."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_to_dashboard", "Dashboard", priority=True),
        Binding("G", "request_ai_resolution", "AI Resolve", key_display="Shift+G"),
        Binding("shift+g", "request_ai_resolution", "AI Resolve", show=False),
        Binding("m", "apply_hunk_suggestion", "Apply Hunk (m)"),
        Binding("n", "next_hunk", "Next Hunk (n)"),
        Binding("p", "prev_hunk", "Prev Hunk (p)"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("c", "goto_commit", "Commit"),
    ]

    def __init__(self, target_file: str | None = None) -> None:
        super().__init__()
        self._target_file = target_file
        self._current_file: str | None = None
        self._file_content: str = ""
        self._hunks: list[ConflictHunk] = []
        self._current_hunk_index: int = 0
        self._conflicted_files: list[str] = []

    @property
    def zit_app(self) -> ZitApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label(
                "⚡ MERGE CONFLICTS",
                id="conflict-title",
                classes="status-badge badge-dirty",
            )
            yield Label(
                "Hunk: --",
                id="conflict-hunk-count",
                classes="status-badge badge-branch",
            )
            yield Label(
                "Shift+G: AI Resolve  |  m: Apply Hunk  |  n/p: Next/Prev Hunk  |  Esc: Dashboard",
                id="conflict-shortcuts",
                classes="status-badge",
            )
        with Horizontal(id="conflict-main"):
            with Vertical(id="conflict-ours-panel"):
                yield Label("⬅ Ours", id="conflict-ours-header", classes="panel-header")
                yield Static(
                    "(Ours content)",
                    id="conflict-ours-content",
                    classes="conflict-side-content",
                )
            with Vertical(id="conflict-center-panel"):
                yield Label(
                    "✨ AI Suggestion / Resolution",
                    id="conflict-center-header",
                    classes="panel-header",
                )
                yield TextArea("", id="conflict-resolution-input")
                yield Static("", id="conflict-ai-explanation")
                with Horizontal(id="conflict-actions"):
                    yield Button(
                        "AI Resolve [Shift+G]",
                        variant="primary",
                        id="btn-ai-resolve",
                    )
                    yield Button(
                        "Apply Hunk [m]",
                        variant="success",
                        id="btn-apply-hunk",
                    )
            with Vertical(id="conflict-theirs-panel"):
                yield Label(
                    "➡ Theirs", id="conflict-theirs-header", classes="panel-header"
                )
                yield Static(
                    "(Theirs content)",
                    id="conflict-theirs-content",
                    classes="conflict-side-content",
                )
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self.load_conflicts()

    def load_conflicts(self) -> None:
        """Discovers conflicted files and loads the first or targeted file."""
        try:
            self._conflicted_files = self.zit_app.git_service.get_conflicted_files()
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Git Error", str(err)))
            return

        if not self._conflicted_files:
            self._show_clean_state()
            return

        # Pick file
        if self._target_file and self._target_file in self._conflicted_files:
            self._current_file = self._target_file
        else:
            self._current_file = self._conflicted_files[0]

        self._load_file(self._current_file)

    def _show_clean_state(self) -> None:
        """Updates UI when no merge conflicts exist."""
        title_lbl = self.query_one("#conflict-title", Label)
        title_lbl.update("✔ No Conflicts")
        title_lbl.set_classes("status-badge badge-clean")

        count_lbl = self.query_one("#conflict-hunk-count", Label)
        count_lbl.update("0 conflicted files")

        ours_lbl = self.query_one("#conflict-ours-content", Static)
        ours_lbl.update("Working tree has no merge conflicts.")

        theirs_lbl = self.query_one("#conflict-theirs-content", Static)
        theirs_lbl.update("Working tree has no merge conflicts.")

        ta = self.query_one("#conflict-resolution-input", TextArea)
        ta.load_text(
            "All conflicts resolved! Press 'c' to commit or Esc for dashboard."
        )

    def _load_file(self, file_path: str) -> None:
        """Loads and parses hunks for a conflicted file."""
        full_path = Path(self.zit_app.repo_path) / file_path
        if not full_path.exists():
            self.app.push_screen(
                ErrorModal("File Error", f"Conflicted file not found: {file_path}")
            )
            return

        try:
            self._file_content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as err:
            self.app.push_screen(
                ErrorModal("Read Error", f"Failed to read '{file_path}': {err}")
            )
            return

        self._hunks = parse_conflicts(self._file_content)
        self._current_hunk_index = 0

        title_lbl = self.query_one("#conflict-title", Label)
        file_idx = (
            self._conflicted_files.index(file_path) + 1
            if file_path in self._conflicted_files
            else 1
        )
        title_lbl.update(
            f"⚡ {file_path} ({file_idx}/{len(self._conflicted_files)} files)"
        )

        self._update_hunk_display()

    def _update_hunk_display(self) -> None:
        """Updates three panels for the current active hunk."""
        count_lbl = self.query_one("#conflict-hunk-count", Label)

        if not self._hunks:
            count_lbl.update("0 hunks remaining")
            self._show_file_resolved()
            return

        total_hunks = len(self._hunks)
        curr = min(self._current_hunk_index, total_hunks - 1)
        self._current_hunk_index = curr
        hunk = self._hunks[curr]

        count_lbl.update(f"Hunk {curr + 1} of {total_hunks}")

        # Update Ours panel
        ours_hdr = self.query_one("#conflict-ours-header", Label)
        ours_hdr.update(f"⬅ Ours ({hunk.ours_label or 'HEAD'})")
        ours_content = self.query_one("#conflict-ours-content", Static)
        ours_content.update(hunk.ours if hunk.ours else "(empty)")

        # Update Theirs panel
        theirs_hdr = self.query_one("#conflict-theirs-header", Label)
        theirs_hdr.update(f"➡ Theirs ({hunk.theirs_label or 'incoming'})")
        theirs_content = self.query_one("#conflict-theirs-content", Static)
        theirs_content.update(hunk.theirs if hunk.theirs else "(empty)")

        # Pre-fill Center TextArea with ours as a starting baseline
        ta = self.query_one("#conflict-resolution-input", TextArea)
        ta.load_text(hunk.ours)

        # Clear AI explanation
        exp_lbl = self.query_one("#conflict-ai-explanation", Static)
        exp_lbl.update("")

    def _show_file_resolved(self) -> None:
        """Handles state when all hunks in current file are resolved."""
        ta = self.query_one("#conflict-resolution-input", TextArea)
        ta.load_text("All hunks in this file have been resolved.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ai-resolve":
            self.action_request_ai_resolution()
        elif event.button.id == "btn-apply-hunk":
            self.action_apply_hunk_suggestion()

    # ── AI Resolution ────────────────────────────────────────────────

    def action_request_ai_resolution(self) -> None:
        """Triggers AI resolution request for the current hunk."""
        if not self._hunks or not self._current_file:
            self.notify("No active conflict hunk to resolve.", severity="warning")
            return

        hunk = self._hunks[self._current_hunk_index]
        self._fetch_ai_resolution(hunk, self._current_file)

    @work(thread=True)
    def _fetch_ai_resolution(self, hunk: ConflictHunk, file_path: str) -> None:
        self.app.call_from_thread(
            self._show_loading, "Asking AI to resolve conflict..."
        )
        try:
            res = self.zit_app.api_client.resolve_conflict(
                file_path=file_path,
                ours=hunk.ours,
                theirs=hunk.theirs,
                base=hunk.base,
                context_before=hunk.context_before,
                context_after=hunk.context_after,
            )
            resolution = res.get("resolution", "")
            explanation = res.get("explanation", "")
            self.app.call_from_thread(
                self._on_ai_resolution_received, resolution, explanation
            )
        except Exception as err:  # noqa: BLE001
            self.app.call_from_thread(
                self.zit_app.show_error, "AI Resolution Error", str(err)
            )
        finally:
            self.app.call_from_thread(self._hide_loading)

    def _on_ai_resolution_received(self, resolution: str, explanation: str) -> None:
        ta = self.query_one("#conflict-resolution-input", TextArea)
        ta.load_text(resolution)
        if explanation:
            exp_lbl = self.query_one("#conflict-ai-explanation", Static)
            exp_lbl.update(f"💡 AI Note: {explanation}")
        self.notify(
            "AI suggestion ready. Review/edit and press 'm' to apply.", title="ZIT"
        )

    # ── Applying resolutions ─────────────────────────────────────────

    def action_apply_hunk_suggestion(self) -> None:
        """Applies current center TextArea resolution to active hunk."""
        if not self._hunks or not self._current_file:
            self.notify("No conflict hunk to apply.", severity="warning")
            return

        hunk = self._hunks[self._current_hunk_index]
        ta = self.query_one("#conflict-resolution-input", TextArea)
        resolution = ta.text

        # Apply resolution to memory content
        self._file_content = apply_hunk_resolution(self._file_content, hunk, resolution)

        # Re-parse remaining hunks
        self._hunks = parse_conflicts(self._file_content)

        if self._hunks:
            # Remaining hunks in this file
            if self._current_hunk_index >= len(self._hunks):
                self._current_hunk_index = max(0, len(self._hunks) - 1)
            self._update_hunk_display()
            self.notify(
                f"Hunk applied! {len(self._hunks)} hunk(s) remaining.",
                title="ZIT",
            )
        else:
            # All hunks in this file are resolved!
            self._save_and_stage_current_file()

    def _save_and_stage_current_file(self) -> None:
        """Writes resolved content to disk and stages the file."""
        if not self._current_file:
            return

        file_path = self._current_file
        full_path = Path(self.zit_app.repo_path) / file_path

        try:
            full_path.write_text(self._file_content, encoding="utf-8")
            self.zit_app.git_service.stage_file(file_path)
            self.notify(
                f"Resolved and staged: {file_path}",
                title="ZIT",
                severity="information",
            )
        except (OSError, GitServiceError) as err:
            self.app.push_screen(
                ErrorModal(
                    "Save/Stage Error", f"Failed to save and stage '{file_path}': {err}"
                )
            )
            return

        # Refresh remaining conflicted files
        try:
            self._conflicted_files = self.zit_app.git_service.get_conflicted_files()
        except GitServiceError:
            self._conflicted_files = []

        if self._conflicted_files:
            # Move to next conflicted file
            self._current_file = self._conflicted_files[0]
            self._load_file(self._current_file)
        else:
            self._show_clean_state()
            self.notify(
                "All merge conflicts resolved! Ready to commit.",
                title="ZIT Success",
                severity="information",
            )

    # ── Navigation & helpers ─────────────────────────────────────────

    def action_next_hunk(self) -> None:
        if not self._hunks:
            return
        if self._current_hunk_index < len(self._hunks) - 1:
            self._current_hunk_index += 1
            self._update_hunk_display()
        else:
            self.notify("Already at last hunk in this file.", severity="information")

    def action_prev_hunk(self) -> None:
        if not self._hunks:
            return
        if self._current_hunk_index > 0:
            self._current_hunk_index -= 1
            self._update_hunk_display()
        else:
            self.notify("Already at first hunk in this file.", severity="information")

    def action_refresh_data(self) -> None:
        self.load_conflicts()
        self.notify("Conflicts refreshed", title="ZIT")

    def action_goto_commit(self) -> None:
        self.zit_app.show_screen("commit")

    def action_back_to_dashboard(self) -> None:
        self.app.pop_screen()

    def _show_loading(self, message: str) -> None:
        overlay = self.query_one(LoadingOverlay)
        overlay.show(message)

    def _hide_loading(self) -> None:
        overlay = self.query_one(LoadingOverlay)
        overlay.hide()
