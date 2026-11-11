"""Time Travel screen for ZIT client – stash, reset, and reflog recovery."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, OptionList, Static
from textual.widgets.option_list import Option

from zit.services.exceptions import GitServiceError
from zit.services.git_service import ReflogEntry, StashEntry
from zit.widgets.confirm_dialog import ConfirmDialog
from zit.widgets.error_panel import ErrorModal
from zit.widgets.input_dialog import InputDialog
from zit.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from zit.app import ZitApp


class TimeTravelScreen(Screen[None]):
    """Stash, reset, and reflog recovery operations."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "go_back", "Dashboard", priority=True),
        Binding("1", "show_stash", "Stash"),
        Binding("2", "show_reset", "Reset"),
        Binding("3", "show_recovery", "Recovery"),
        Binding("s", "stash_save", "Save Stash"),
        Binding("a", "stash_apply", "Apply Stash"),
        Binding("d", "stash_drop", "Drop Stash"),
        Binding("p", "stash_pop", "Pop Stash"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._active_tab: str = "stash"
        self._stash_entries: list[StashEntry] = []
        self._reflog_entries: list[ReflogEntry] = []

    @property
    def zit_app(self) -> ZitApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label("⏰ TIME TRAVEL", classes="status-badge badge-branch")
            yield Label(
                "1: Stash  |  2: Reset  |  3: Recovery  |  r: Refresh  |  Esc: Dashboard",
                classes="status-badge",
            )
        with Horizontal(id="time-travel-main"):
            with Vertical(id="time-travel-left"):
                yield Label(
                    "📦 Stash / Reflog Entries",
                    id="tt-panel-header",
                    classes="panel-header",
                )
                yield OptionList(id="tt-options")
            with Vertical(id="time-travel-right"):
                yield Label("Details", id="tt-detail-header", classes="panel-header")
                yield Static(
                    "Select an entry from the left panel to inspect.",
                    id="tt-detail-content",
                )
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self._load_stash_tab()

    # ── Tab switching ────────────────────────────────────────────────

    def action_show_stash(self) -> None:
        self._active_tab = "stash"
        self._load_stash_tab()

    def action_show_reset(self) -> None:
        self._active_tab = "reset"
        self._load_reset_tab()

    def action_show_recovery(self) -> None:
        self._active_tab = "recovery"
        self._load_recovery_tab()

    # ── Data loaders ─────────────────────────────────────────────────

    def _load_stash_tab(self) -> None:
        header = self.query_one("#tt-panel-header", Label)
        header.update("📦 Stash Entries  [s: Save  a: Apply  d: Drop  p: Pop]")
        detail_header = self.query_one("#tt-detail-header", Label)
        detail_header.update("Stash Details")
        self._update_detail("Select a stash entry to inspect.")
        options = self.query_one("#tt-options", OptionList)
        options.clear_options()
        try:
            self._stash_entries = self.zit_app.git_service.stash_list()
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Stash Error", str(err)))
            return

        if not self._stash_entries:
            options.add_option(Option("(No stashes saved)", id="empty"))
            return

        for entry in self._stash_entries:
            branch_info = f" on {entry.branch}" if entry.branch else ""
            label = f"stash@{{{entry.index}}}{branch_info}: {entry.message}"
            options.add_option(Option(label, id=f"stash-{entry.index}"))

    def _load_reset_tab(self) -> None:
        header = self.query_one("#tt-panel-header", Label)
        header.update("🔄 Reset HEAD  [Choose a mode below]")
        detail_header = self.query_one("#tt-detail-header", Label)
        detail_header.update("Reset Modes")
        options = self.query_one("#tt-options", OptionList)
        options.clear_options()
        options.add_option(
            Option(
                "🟢 Soft Reset  –  Keep staged & working tree changes", id="reset-soft"
            )
        )
        options.add_option(
            Option(
                "🟡 Mixed Reset  –  Unstage changes, keep working tree",
                id="reset-mixed",
            )
        )
        options.add_option(
            Option(
                "🔴 Hard Reset  –  Discard ALL changes (DESTRUCTIVE)", id="reset-hard"
            )
        )
        self._update_detail(
            "Soft Reset:\n"
            "  Moves HEAD back but keeps your staged changes and working tree intact.\n"
            "  Useful for re-doing commits.\n\n"
            "Mixed Reset (default git behavior):\n"
            "  Moves HEAD back and unstages changes, but keeps working tree modifications.\n"
            "  Useful for re-staging selectively.\n\n"
            "Hard Reset:\n"
            "  ⚠️  Moves HEAD back AND discards ALL working tree and index changes.\n"
            "  This is DESTRUCTIVE and cannot be easily undone.\n"
            "  Your current changes will be permanently lost."
        )

    def _load_recovery_tab(self) -> None:
        header = self.query_one("#tt-panel-header", Label)
        header.update("🔮 Reflog Recovery  [Enter: Restore HEAD to entry]")
        detail_header = self.query_one("#tt-detail-header", Label)
        detail_header.update("Reflog Entry Details")
        self._update_detail("Select a reflog entry to inspect.")
        options = self.query_one("#tt-options", OptionList)
        options.clear_options()
        try:
            self._reflog_entries = self.zit_app.git_service.get_reflog(limit=50)
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Reflog Error", str(err)))
            return

        if not self._reflog_entries:
            options.add_option(Option("(No reflog entries)", id="empty"))
            return

        for i, entry in enumerate(self._reflog_entries):
            label = f"{entry.selector}  {entry.hash}  {entry.action}: {entry.message}"
            options.add_option(Option(label, id=f"reflog-{i}"))

    # ── List selection ───────────────────────────────────────────────

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if not event.option_id or event.option_id == "empty":
            return

        if self._active_tab == "stash" and event.option_id.startswith("stash-"):
            idx = int(event.option_id.split("-", 1)[1])
            for entry in self._stash_entries:
                if entry.index == idx:
                    self._update_detail(
                        f"Stash Index:  {entry.index}\n"
                        f"Branch:       {entry.branch or '(unknown)'}\n"
                        f"Hash:         {entry.hash}\n"
                        f"Message:      {entry.message}\n\n"
                        "Actions:\n"
                        "  a  Apply (keep stash)\n"
                        "  p  Pop (apply & remove)\n"
                        "  d  Drop (remove without applying)"
                    )
                    break

        elif self._active_tab == "recovery" and event.option_id.startswith("reflog-"):
            idx = int(event.option_id.split("-", 1)[1])
            if 0 <= idx < len(self._reflog_entries):
                entry = self._reflog_entries[idx]
                self._update_detail(
                    f"Selector:  {entry.selector}\n"
                    f"Hash:      {entry.hash}\n"
                    f"Action:    {entry.action}\n"
                    f"Message:   {entry.message}\n\n"
                    "Press Enter to restore HEAD to this point.\n"
                    "⚠️  This will perform a hard reset."
                )

        elif self._active_tab == "reset" and event.option_id.startswith("reset-"):
            mode = event.option_id.split("-", 1)[1]
            descriptions = {
                "soft": (
                    "🟢 Soft Reset\n\n"
                    "Moves HEAD to the target commit.\n"
                    "Index (staged area) and working tree are PRESERVED.\n\n"
                    "Use case: Undo the last commit but keep your changes staged\n"
                    "for a new commit."
                ),
                "mixed": (
                    "🟡 Mixed Reset\n\n"
                    "Moves HEAD to the target commit.\n"
                    "Index is reset (changes become unstaged).\n"
                    "Working tree is PRESERVED.\n\n"
                    "Use case: Undo commits and unstage changes for selective re-staging."
                ),
                "hard": (
                    "🔴 Hard Reset  ⚠️  DESTRUCTIVE\n\n"
                    "Moves HEAD to the target commit.\n"
                    "Index AND working tree are RESET.\n"
                    "ALL uncommitted changes will be PERMANENTLY LOST.\n\n"
                    "Use case: Completely discard recent work and start fresh."
                ),
            }
            self._update_detail(descriptions.get(mode, ""))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if not event.option_id or event.option_id == "empty":
            return

        if self._active_tab == "reset" and event.option_id.startswith("reset-"):
            mode = event.option_id.split("-", 1)[1]
            self._do_reset(mode)

        elif self._active_tab == "recovery" and event.option_id.startswith("reflog-"):
            idx = int(event.option_id.split("-", 1)[1])
            if 0 <= idx < len(self._reflog_entries):
                entry = self._reflog_entries[idx]
                self._do_reflog_restore(entry)

    # ── Stash actions ────────────────────────────────────────────────

    def action_stash_save(self) -> None:
        if self._active_tab != "stash":
            self.action_show_stash()

        def _on_name(name: str | None) -> None:
            if not name:
                return
            try:
                self.zit_app.git_service.stash_save(name)
                self.notify(f"Stash saved: {name}", title="ZIT")
                self._load_stash_tab()
            except GitServiceError as err:
                self.app.push_screen(ErrorModal("Stash Error", str(err)))

        self.app.push_screen(
            InputDialog(
                title="Save Stash",
                prompt="Enter a descriptive name for this stash:",
                placeholder="e.g. WIP feature-x",
                confirm_label="Save",
            ),
            callback=_on_name,
        )

    def _get_selected_stash_index(self) -> int | None:
        options = self.query_one("#tt-options", OptionList)
        idx = options.highlighted
        if idx is None:
            return None
        opt = options.get_option_at_index(idx)
        if opt.id and opt.id.startswith("stash-"):
            return int(opt.id.split("-", 1)[1])
        return None

    def action_stash_apply(self) -> None:
        if self._active_tab != "stash":
            self.notify("Switch to Stash tab first (press 1)", severity="warning")
            return
        idx = self._get_selected_stash_index()
        if idx is None:
            self.notify("Select a stash entry first.", severity="warning")
            return

        def _on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                self.zit_app.git_service.stash_apply(idx)
                self.notify(f"Applied stash@{{{idx}}}", title="ZIT")
                self._load_stash_tab()
            except GitServiceError as err:
                self.app.push_screen(ErrorModal("Stash Error", str(err)))

        self.app.push_screen(
            ConfirmDialog(
                title="Apply Stash",
                message=f"Apply stash@{{{idx}}} to your working tree?",
                details="The stash will remain in the list after applying.",
                confirm_label="Apply",
            ),
            callback=_on_confirm,
        )

    def action_stash_pop(self) -> None:
        if self._active_tab != "stash":
            self.notify("Switch to Stash tab first (press 1)", severity="warning")
            return
        idx = self._get_selected_stash_index()
        if idx is None:
            self.notify("Select a stash entry first.", severity="warning")
            return

        def _on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                self.zit_app.git_service.stash_pop(idx)
                self.notify(f"Popped stash@{{{idx}}}", title="ZIT")
                self._load_stash_tab()
            except GitServiceError as err:
                self.app.push_screen(ErrorModal("Stash Error", str(err)))

        self.app.push_screen(
            ConfirmDialog(
                title="Pop Stash",
                message=f"Apply and remove stash@{{{idx}}}?",
                details="The stash entry will be removed after applying.",
                confirm_label="Pop",
            ),
            callback=_on_confirm,
        )

    def action_stash_drop(self) -> None:
        if self._active_tab != "stash":
            self.notify("Switch to Stash tab first (press 1)", severity="warning")
            return
        idx = self._get_selected_stash_index()
        if idx is None:
            self.notify("Select a stash entry first.", severity="warning")
            return

        def _on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                self.zit_app.git_service.stash_drop(idx)
                self.notify(f"Dropped stash@{{{idx}}}", title="ZIT")
                self._load_stash_tab()
            except GitServiceError as err:
                self.app.push_screen(ErrorModal("Stash Error", str(err)))

        self.app.push_screen(
            ConfirmDialog(
                title="Drop Stash",
                message=f"Permanently remove stash@{{{idx}}}?",
                details=f"stash@{{{idx}}} will be permanently deleted and cannot be recovered.",
                confirm_label="Drop",
            ),
            callback=_on_confirm,
        )

    # ── Reset actions ────────────────────────────────────────────────

    def _do_reset(self, mode: str) -> None:
        descriptions = {
            "soft": "HEAD will move back. Staged and working tree changes are preserved.",
            "mixed": "HEAD will move back. Staged changes become unstaged. Working tree is preserved.",
            "hard": "HEAD will move back. ALL staged and working tree changes will be PERMANENTLY LOST.",
        }
        detail = descriptions.get(mode, "")

        def _on_target(target: str | None) -> None:
            if not target:
                return

            def _on_confirm(confirmed: bool) -> None:
                if not confirmed:
                    return
                try:
                    self.zit_app.git_service.reset(mode, target)
                    self.notify(f"Reset ({mode}) to {target} successful", title="ZIT")
                    self._load_reset_tab()
                except GitServiceError as err:
                    self.app.push_screen(ErrorModal("Reset Error", str(err)))

            self.app.push_screen(
                ConfirmDialog(
                    title=f"{mode.capitalize()} Reset to '{target}'",
                    message=f"Are you sure you want to perform a {mode} reset to '{target}'?",
                    details=detail,
                    confirm_label=f"Reset ({mode})",
                ),
                callback=_on_confirm,
            )

        self.app.push_screen(
            InputDialog(
                title=f"{mode.capitalize()} Reset",
                prompt="Enter the target commit reference:",
                initial_value="HEAD~1",
                placeholder="e.g. HEAD~1, abc1234, main",
                confirm_label="Next",
            ),
            callback=_on_target,
        )

    # ── Reflog restore ───────────────────────────────────────────────

    def _do_reflog_restore(self, entry: ReflogEntry) -> None:
        def _on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                self.zit_app.git_service.restore_to_reflog(entry.selector)
                self.notify(
                    f"HEAD restored to {entry.selector} ({entry.hash})", title="ZIT"
                )
                self._load_recovery_tab()
            except GitServiceError as err:
                self.app.push_screen(ErrorModal("Recovery Error", str(err)))

        self.app.push_screen(
            ConfirmDialog(
                title="Restore HEAD from Reflog",
                message=(
                    f"Restore HEAD to {entry.selector}?\n"
                    f"Hash: {entry.hash}\n"
                    f"Action: {entry.action}: {entry.message}"
                ),
                details=(
                    "This performs a hard reset to the selected reflog entry.\n"
                    "ALL current uncommitted changes will be PERMANENTLY LOST."
                ),
                confirm_label="Restore",
            ),
            callback=_on_confirm,
        )

    # ── Helpers ───────────────────────────────────────────────────────

    def _update_detail(self, text: str) -> None:
        content = self.query_one("#tt-detail-content", Static)
        content.update(text)

    def action_refresh_data(self) -> None:
        if self._active_tab == "stash":
            self._load_stash_tab()
        elif self._active_tab == "reset":
            self._load_reset_tab()
        elif self._active_tab == "recovery":
            self._load_recovery_tab()
        self.notify("Refreshed", title="ZIT")

    def action_go_back(self) -> None:
        self.app.pop_screen()
