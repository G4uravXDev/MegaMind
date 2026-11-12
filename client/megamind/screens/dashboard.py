"""Dashboard screen for MEGAMIND client."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label

from megamind.services.exceptions import GitServiceError
from megamind.widgets.commit_list import CommitList
from megamind.widgets.error_panel import ErrorModal
from megamind.widgets.file_list import FileList
from megamind.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from megamind.app import MegaMindApp


class DashboardScreen(Screen[None]):
    """Main landing dashboard screen."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit_app", "Quit", priority=True),
        Binding("r", "refresh_data", "Refresh"),
        Binding("s", "goto_staging", "Staging"),
        Binding("c", "goto_commit", "Commit"),
        Binding("b", "goto_branches", "Branches"),
        Binding("l", "goto_log", "Log Graph"),
        Binding("t", "goto_time_travel", "Time Travel"),
        Binding("m", "goto_conflicts", "Conflicts"),
        Binding("a", "goto_mentor", "AI Mentor"),
        Binding("v", "generate_coverage", "Coverage"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._has_conflicts = False

    @property
    def megamind_app(self) -> MegaMindApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label(
                "Branch: --", id="status-branch", classes="status-badge badge-branch"
            )
            yield Label("Health: --", id="status-health", classes="status-badge")
            yield Label("Sync: --", id="status-sync", classes="status-badge badge-sync")
        with Horizontal(id="dashboard-main"):
            with Vertical(id="dashboard-left"):
                yield Label("📁 Working Tree & Staged Files", classes="panel-header")
                yield FileList(id="dashboard-files")
            with Vertical(id="dashboard-right"):
                yield Label("📜 Recent Commits", classes="panel-header")
                yield CommitList(id="dashboard-commits")
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        """Fetches repo health, status, and commits safely."""
        try:
            git_service = self.megamind_app.git_service
            health = git_service.get_repo_health()
            self._has_conflicts = health.has_conflicts

            # Update Branch label
            branch_lbl = self.query_one("#status-branch", Label)
            branch_lbl.update(f"⎇  Branch: {health.branch}")

            # Update Health label
            health_lbl = self.query_one("#status-health", Label)
            if health.has_conflicts:
                health_lbl.update("⚡ CONFLICTS PRESENT")
                health_lbl.set_classes("status-badge badge-dirty")
            elif health.is_clean:
                health_lbl.update("✔ Clean working tree")
                health_lbl.set_classes("status-badge badge-clean")
            else:
                health_lbl.update("● Working tree dirty")
                health_lbl.set_classes("status-badge badge-dirty")

            # Update Sync label (ahead/behind)
            sync_lbl = self.query_one("#status-sync", Label)
            if health.has_remote:
                sync_lbl.update(f"↑ {health.ahead}  ↓ {health.behind}")
            else:
                sync_lbl.update("No tracking remote")

            # Update Files
            status = git_service.get_status_entries()
            file_list = self.query_one("#dashboard-files", FileList)
            file_list.set_files(
                staged=status["staged"],
                unstaged=status["unstaged"],
                untracked=status["untracked"],
                conflicted=status["conflicted"],
            )

            # Update Commits
            commits = git_service.get_recent_commits(limit=15)
            commit_list = self.query_one("#dashboard-commits", CommitList)
            commit_list.set_commits(commits)

        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Git Error", str(err)))
        except Exception as err:  # noqa: BLE001
            self.app.push_screen(ErrorModal("Unexpected Error", str(err)))

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_refresh_data(self) -> None:
        self.refresh_dashboard()
        self.notify("Dashboard refreshed", title="MEGAMIND")

    def action_goto_staging(self) -> None:
        self.megamind_app.show_screen("staging")

    def action_goto_commit(self) -> None:
        self.megamind_app.show_screen("commit")

    def action_goto_branches(self) -> None:
        self.megamind_app.show_screen("branches")

    def action_goto_log(self) -> None:
        self.megamind_app.show_screen("log")

    def action_goto_time_travel(self) -> None:
        self.megamind_app.show_screen("time_travel")

    def action_goto_conflicts(self) -> None:
        if not self._has_conflicts:
            self.notify("No merge conflicts in repository.", severity="information")
            return
        self.megamind_app.show_screen("conflicts")

    def action_goto_mentor(self) -> None:
        self.megamind_app.show_screen("mentor")

    def action_generate_coverage(self) -> None:
        file_list = self.query_one("#dashboard-files", FileList)
        selected = file_list.get_selected_item()
        if not selected:
            self.notify("Select a file first to generate coverage.", severity="warning")
            return
        self.megamind_app.generate_coverage_for_file(selected.path)
