"""Main Textual Application for MEGAMIND."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from textual import work
from textual.app import App
from textual.binding import Binding
from textual.screen import Screen

from megamind.config import config
from megamind.screens.branches import BranchesScreen
from megamind.screens.commit import CommitScreen
from megamind.screens.conflicts import ConflictResolutionScreen
from megamind.screens.dashboard import DashboardScreen
from megamind.screens.log_graph import LogGraphScreen
from megamind.screens.mentor import MentorScreen
from megamind.screens.staging import StagingScreen
from megamind.screens.time_travel import TimeTravelScreen
from megamind.services.api_client import ApiClient
from megamind.services.exceptions import (
    ApiClientError,
    GitServiceError,
    RepoNotFoundError,
)
from megamind.services.git_service import GitService
from megamind.widgets.coverage_modal import CoverageModal
from megamind.widgets.error_panel import ErrorModal
from megamind.widgets.help_overlay import HelpModal


class MegaMindApp(App[None]):
    """AI-powered Git assistant terminal client."""

    CSS_PATH = Path(__file__).parent / "styles" / "megamind.tcss"
    TITLE = "MegaMind - AI Git Assistant"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_to_dashboard", "Dashboard"),
        Binding("question_mark", "show_help", "Help (?)", priority=True),
        Binding("?", "show_help", "Help", show=False, priority=True),
        Binding("f1", "show_help", "Help", show=False, priority=True),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, repo_path: Path | str | None = None) -> None:
        super().__init__()
        self.repo_path = Path(repo_path) if repo_path else config.repo_path
        self._git_service: GitService | None = None
        self._api_client = ApiClient()
        self._screen_registry: dict[str, Screen[Any]] = {}

    @property
    def git_service(self) -> GitService:
        if self._git_service is None:
            self._git_service = GitService(self.repo_path)
        return self._git_service

    @property
    def api_client(self) -> ApiClient:
        return self._api_client

    def on_mount(self) -> None:
        try:
            # Initialize Git service to test repo validity
            _ = self.git_service
            self.push_screen(DashboardScreen())
        except RepoNotFoundError as err:
            self.push_screen(DashboardScreen())
            self.push_screen(
                ErrorModal(
                    "Not a Git Repository",
                    f"{err}\nPlease run megamind from inside an initialized git repository.",
                )
            )
        except Exception as err:  # noqa: BLE001
            self.push_screen(DashboardScreen())
            self.push_screen(ErrorModal("Initialization Error", str(err)))

    def register_screen(self, name: str, screen: Screen[Any]) -> None:
        """Registers a named screen."""
        self._screen_registry[name] = screen

    def show_screen(self, name: str) -> None:
        """Navigates to a named screen or alerts if not yet registered."""
        if name == "staging":
            self.push_screen(StagingScreen())
        elif name == "commit":
            self.push_screen(CommitScreen())
        elif name == "branches":
            self.push_screen(BranchesScreen())
        elif name == "log":
            self.push_screen(LogGraphScreen())
        elif name == "time_travel":
            self.push_screen(TimeTravelScreen())
        elif name == "conflicts":
            self.push_screen(ConflictResolutionScreen())
        elif name == "mentor":
            self.push_screen(MentorScreen())
        elif name in self._screen_registry:
            self.push_screen(self._screen_registry[name])
        else:
            self.notify(
                f"{name.capitalize()} screen will be activated in the next milestone.",
                title="MEGAMIND Navigation",
                severity="information",
            )

    def action_back_to_dashboard(self) -> None:
        """Pops screens back to the root Dashboard."""
        while len(self.screen_stack) > 1 and not isinstance(
            self.screen, DashboardScreen
        ):
            self.pop_screen()

    def action_show_help(self) -> None:
        """Pushes the Help overlay modal."""
        self.push_screen(HelpModal())

    def show_error(self, title: str, message: str) -> None:
        """Pushes a non-fatal modal error dialog."""
        self.push_screen(ErrorModal(title, message))

    @work(thread=True)
    def generate_coverage_for_file(self, file_path: str) -> None:
        """Fetches AI test coverage in a background worker."""
        try:
            target = Path(self.repo_path) / file_path
            if not target.exists() or target.is_dir():
                self.call_from_thread(
                    self.notify, f"Cannot read {file_path}", severity="error"
                )
                return

            self.call_from_thread(
                self.notify, f"Generating tests for {file_path}...", title="MegaMind AI"
            )
            source = target.read_text(encoding="utf-8", errors="replace")
            tests = self.api_client.coverage(file_path, source)

            # Show generated coverage result in CoverageModal
            self.call_from_thread(
                self.push_screen,
                CoverageModal(file_path, tests),
            )
        except (ApiClientError, GitServiceError) as err:
            self.call_from_thread(self.show_error, "AI Coverage Error", str(err))
        except Exception as err:  # noqa: BLE001
            self.call_from_thread(self.show_error, "Unexpected Error", str(err))
