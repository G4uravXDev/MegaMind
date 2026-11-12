"""Log graph screen for visualizing all-branch commit history and details."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, OptionList, Static
from textual.widgets.option_list import Option

from megamind.services.exceptions import GitServiceError
from megamind.services.git_service import CommitDetails, LogGraphEntry
from megamind.widgets.error_panel import ErrorModal
from megamind.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from megamind.app import MegaMindApp


class LogGraphScreen(Screen[None]):
    """Visualizes git log --graph --all with interactive commit details."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_to_dashboard", "Dashboard"),
        Binding("enter", "view_commit", "View Details"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[LogGraphEntry] = []
        self._hash_map: dict[str, str] = {}  # option_id -> commit_hash

    @property
    def megamind_app(self) -> MegaMindApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label(
                "📊 ALL BRANCHES COMMIT GRAPH", classes="status-badge badge-branch"
            )
            yield Label(
                "↑/↓: Browse Graph  |  Enter: View Commit Details  |  Esc: Dashboard",
                classes="status-badge",
            )
        with Horizontal(id="log-main"):
            with Vertical(id="log-left"):
                yield Label("📜 Commit Graph (--graph --all)", classes="panel-header")
                yield OptionList(id="graph-options")
            with Vertical(id="log-right"):
                yield Label("🔍 Commit Details & Changed Files", classes="panel-header")
                with VerticalScroll(id="commit-detail-scroll"):
                    yield Static(id="commit-detail-content")
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_graph()

    def refresh_graph(self) -> None:
        """Loads log graph entries and populates the option list."""
        try:
            git_service = self.megamind_app.git_service
            self._entries = git_service.get_log_graph(max_count=100)

            option_list = self.query_one("#graph-options", OptionList)
            prev_idx = option_list.highlighted or 0
            option_list.clear_options()
            self._hash_map.clear()

            if not self._entries:
                empty = Text("  (No commits in this repository)", style="dim italic")
                option_list.add_option(Option(empty, disabled=True))
                self._show_commit_details(None)
                return

            options: list[Option] = []
            first_hash: str | None = None
            for idx, entry in enumerate(self._entries):
                label = self._render_graph_line(entry)
                opt_id = f"entry-{idx}"
                if entry.commit_hash:
                    self._hash_map[opt_id] = entry.commit_hash
                    if not first_hash:
                        first_hash = entry.commit_hash
                options.append(Option(label, id=opt_id))

            option_list.add_options(options)
            option_list.highlighted = min(prev_idx, len(options) - 1)

            # Show details for initial commit
            if first_hash:
                self._load_and_show_commit(first_hash)

        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Git Error", str(err)))
        except Exception as err:  # noqa: BLE001
            self.app.push_screen(ErrorModal("Unexpected Error", str(err)))

    def _render_graph_line(self, entry: LogGraphEntry) -> Text:
        """Renders rich syntax for git graph lines."""
        text = Text()

        # Graph node symbols
        text.append(f"{entry.graph} ", style="bold yellow")

        if entry.commit_hash:
            text.append(f"{entry.commit_hash} ", style="bold cyan")

            if entry.refs:
                text.append(f"{entry.refs} ", style="bold green")

            if entry.date:
                text.append(f"({entry.date}) ", style="dim")

            if entry.author:
                text.append(f"[{entry.author}] ", style="magenta")

            text.append(entry.subject, style="white")

        return text

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if event.option_id and event.option_id in self._hash_map:
            commit_hash = self._hash_map[event.option_id]
            self._load_and_show_commit(commit_hash)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id and event.option_id in self._hash_map:
            commit_hash = self._hash_map[event.option_id]
            self._load_and_show_commit(commit_hash)

    def action_view_commit(self) -> None:
        """Shows details for the highlighted commit."""
        option_list = self.query_one("#graph-options", OptionList)
        idx = option_list.highlighted
        if idx is not None and 0 <= idx < len(self._entries):
            entry = self._entries[idx]
            if entry.commit_hash:
                self._load_and_show_commit(entry.commit_hash)

    def _load_and_show_commit(self, commit_hash: str) -> None:
        try:
            details = self.megamind_app.git_service.get_commit_details(commit_hash)
            self._show_commit_details(details)
        except Exception as err:  # noqa: BLE001
            static = self.query_one("#commit-detail-content", Static)
            static.update(Text(f"Could not load details: {err}", style="dim red"))

    def _show_commit_details(self, details: CommitDetails | None) -> None:
        """Renders commit details and changed file list in the right panel."""
        static = self.query_one("#commit-detail-content", Static)
        if not details:
            static.update(
                Text("Select a commit from the graph to inspect.", style="dim italic")
            )
            return

        text = Text()
        text.append(f"Commit:  {details.full_hash}\n", style="bold yellow")
        text.append(
            f"Author:  {details.author} <{details.author_email}>\n", style="bold cyan"
        )
        text.append(f"Date:    {details.date}\n", style="dim")
        text.append(
            f"Summary: +{details.total_insertions} / -{details.total_deletions} lines across {len(details.files)} file(s)\n\n",
            style="bold green",
        )

        text.append(
            "── Message ──────────────────────────────────────────\n",
            style="bold white",
        )
        text.append(f"{details.message.strip()}\n\n", style="white")

        text.append(
            "── Changed Files ────────────────────────────────────\n",
            style="bold white",
        )
        if not details.files:
            text.append(
                "(No files changed / initial empty commit)\n", style="dim italic"
            )
        else:
            for f in details.files:
                badge = f"[{f.change_type}]"
                text.append(f"{badge:5s} ", style="bold yellow")
                text.append(f"{f.path:35s} ", style="bold white")
                text.append(f"+{f.insertions:<4d} ", style="green")
                text.append(f"-{f.deletions:<4d}\n", style="red")

        static.update(text)

    def action_refresh_data(self) -> None:
        self.refresh_graph()
        self.notify("Log graph refreshed", title="MEGAMIND")

    def action_back_to_dashboard(self) -> None:
        self.megamind_app.action_back_to_dashboard()

    def action_quit_app(self) -> None:
        self.app.exit()
