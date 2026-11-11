"""Commit screen for staging review and AI-powered commit creation."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, TextArea

from zit.services.exceptions import ApiClientError, GitServiceError
from zit.widgets.error_panel import ErrorModal
from zit.widgets.file_list import FileList
from zit.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from zit.app import ZitApp


class CommitScreen(Screen[None]):
    """Interactive commit creation screen with AI commit message generation."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_to_dashboard", "Dashboard"),
        Binding("ctrl+s", "submit_commit", "Commit (Ctrl+S)"),
        Binding("g", "generate_ai_message", "AI Message (g)"),
        Binding("s", "goto_staging", "Staging"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    @property
    def zit_app(self) -> ZitApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label("💾 COMMIT WORKSPACE", classes="status-badge badge-branch")
            yield Label(
                "g: Generate AI Message  |  Ctrl+S: Commit  |  s: Go to Staging",
                classes="status-badge",
            )
        with Horizontal(id="commit-main"):
            with Vertical(id="commit-left"):
                yield Label("📋 Staged Files for Commit", classes="panel-header")
                yield FileList(id="commit-staged-files")
            with Vertical(id="commit-right"):
                yield Label(
                    "📝 Commit Message (Editable):",
                    classes="panel-header",
                    id="commit-msg-header",
                )
                yield TextArea(id="commit-message-input")
                with Horizontal(id="commit-actions"):
                    yield Button(
                        "✨ Generate with AI [g]",
                        variant="primary",
                        id="btn-ai-gen",
                    )
                    yield Button(
                        "Commit Changes [Ctrl+S]",
                        variant="success",
                        id="btn-do-commit",
                    )
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_commit_view()

    def refresh_commit_view(self) -> None:
        """Loads currently staged files."""
        try:
            git_service = self.zit_app.git_service
            staged = git_service.get_staged_files()

            file_list = self.query_one("#commit-staged-files", FileList)
            file_list.set_files(staged=staged)

            header = self.query_one("#commit-msg-header", Label)
            if staged:
                header.update(f"📝 Commit Message ({len(staged)} staged file(s)):")
            else:
                header.update("⚠️  No files staged! Go to Staging (s) to stage files.")

        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Git Error", str(err)))
        except Exception as err:  # noqa: BLE001
            self.app.push_screen(ErrorModal("Unexpected Error", str(err)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ai-gen":
            self.action_generate_ai_message()
        elif event.button.id == "btn-do-commit":
            self.action_submit_commit()

    def action_generate_ai_message(self) -> None:
        """Triggers AI message generation in background worker."""
        git_service = self.zit_app.git_service
        staged = git_service.get_staged_files()
        if not staged:
            self.notify(
                "No files staged to generate a commit message for. Press 's' to stage files.",
                severity="warning",
            )
            return

        self._generate_message_worker()

    @work(thread=True)
    def _generate_message_worker(self) -> None:
        """Worker thread fetching AI commit message."""
        loading = self.query_one(LoadingOverlay)
        self.app.call_from_thread(loading.show, "Generating commit message with AI...")

        try:
            git_service = self.zit_app.git_service
            diff = git_service.get_staged_diff()
            recent_commits = [
                c.message for c in git_service.get_recent_commits(limit=10)
            ]

            message = self.zit_app.api_client.commit_message(diff, recent_commits)

            self.app.call_from_thread(self._set_commit_message, message)
            self.app.call_from_thread(
                self.notify, "AI commit message generated!", title="ZIT AI"
            )
        except (ApiClientError, GitServiceError) as err:
            self.app.call_from_thread(
                self.app.push_screen,
                ErrorModal("AI Generation Error", str(err)),
            )
        except Exception as err:  # noqa: BLE001
            self.app.call_from_thread(
                self.app.push_screen,
                ErrorModal("Unexpected Error", str(err)),
            )
        finally:
            self.app.call_from_thread(loading.hide)

    def _set_commit_message(self, message: str) -> None:
        """Sets the generated message into the TextArea."""
        text_area = self.query_one("#commit-message-input", TextArea)
        text_area.load_text(message)
        text_area.focus()

    def action_submit_commit(self) -> None:
        """Performs the git commit."""
        git_service = self.zit_app.git_service
        staged = git_service.get_staged_files()

        # Validation 1: Nothing staged
        if not staged:
            self.notify(
                "Cannot commit: Nothing staged! Press 's' to go to staging.",
                severity="error",
                title="Commit Blocked",
            )
            return

        # Validation 2: Empty message
        text_area = self.query_one("#commit-message-input", TextArea)
        message = text_area.text.strip()
        if not message:
            self.notify(
                "Cannot commit: Commit message cannot be empty! Type a message or press 'g'.",
                severity="error",
                title="Commit Blocked",
            )
            return

        try:
            git_service.commit(message)
            self.notify(
                f"Committed: {message.splitlines()[0]}",
                title="Commit Successful",
                severity="information",
            )
            self.zit_app.action_back_to_dashboard()
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Commit Failed", str(err)))

    def action_goto_staging(self) -> None:
        self.zit_app.show_screen("staging")

    def action_refresh_data(self) -> None:
        self.refresh_commit_view()
        self.notify("Commit view refreshed", title="ZIT")

    def action_back_to_dashboard(self) -> None:
        self.zit_app.action_back_to_dashboard()

    def action_quit_app(self) -> None:
        self.app.exit()
