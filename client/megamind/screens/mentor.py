"""AI Mentor chat screen for MEGAMIND client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static

from megamind.services.exceptions import ApiClientError, GitServiceError
from megamind.widgets.error_panel import ErrorModal
from megamind.widgets.loading import LoadingOverlay

if TYPE_CHECKING:
    from megamind.app import MegaMindApp


class MentorScreen(Screen[None]):
    """Interactive AI Git Mentor chat view with contextual repository awareness."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_to_dashboard", "Dashboard", priority=True),
        Binding("c", "clear_chat", "Clear Chat"),
        Binding("r", "refresh_context", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._conversation_id: str | None = None

    @property
    def megamind_app(self) -> MegaMindApp:
        return self.app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="repo-status-bar"):
            yield Label(
                "🧠 AI GIT MENTOR",
                classes="status-badge badge-branch",
            )
            yield Label(
                "Repo: Loading context...",
                id="mentor-context-lbl",
                classes="status-badge",
            )
            yield Label(
                "Enter: Send Question  |  c: Clear  |  Esc: Dashboard",
                classes="status-badge",
            )
        with Vertical(id="mentor-main"):
            with VerticalScroll(id="mentor-chat-scroll"):
                yield Static(
                    "👋 Welcome to MegaMind AI Mentor! Ask any plain-English Git question.\n"
                    "I have live context on your active branch, commits, and working tree.",
                    classes="chat-msg chat-system",
                )
            with Horizontal(id="mentor-input-bar"):
                yield Input(
                    placeholder="Ask a Git question (e.g. 'How do I undo my last commit?')...",
                    id="mentor-question-input",
                )
                yield Button("Send", variant="primary", id="btn-mentor-send")
        yield LoadingOverlay()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_repo_context()
        input_widget = self.query_one("#mentor-question-input", Input)
        input_widget.focus()

    def refresh_repo_context(self) -> None:
        """Fetches and displays current repository status context."""
        try:
            gs = self.megamind_app.git_service
            health = gs.get_repo_health()
            staged = len(gs.get_staged_files())
            unstaged = len(gs.get_unstaged_files())
            context_lbl = self.query_one("#mentor-context-lbl", Label)
            conflict_str = " | ⚡ CONFLICTS" if health.has_conflicts else ""
            context_lbl.update(
                f"Branch: {health.branch}  |  Staged: {staged}  |  Unstaged: {unstaged}{conflict_str}"
            )
        except GitServiceError as err:
            self.app.push_screen(ErrorModal("Git Error", str(err)))

    def _get_current_repo_context(self) -> dict[str, Any]:
        """Gathers real-time repo context to send to the mentor API."""
        try:
            gs = self.megamind_app.git_service
            health = gs.get_repo_health()
            staged = gs.get_staged_files()
            unstaged = gs.get_unstaged_files()
            recent = [c.message for c in gs.get_recent_commits(limit=5)]
            return {
                "branch": health.branch,
                "staged_count": len(staged),
                "unstaged_count": len(unstaged),
                "recent_commits": recent,
                "conflicts": health.has_conflicts,
            }
        except Exception:  # noqa: BLE001
            return {
                "branch": "unknown",
                "staged_count": 0,
                "unstaged_count": 0,
                "recent_commits": [],
                "conflicts": False,
            }

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit_question(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-mentor-send":
            input_widget = self.query_one("#mentor-question-input", Input)
            self.submit_question(input_widget.value)

    def submit_question(self, question: str) -> None:
        """Sends the question to the AI mentor and renders conversation turns."""
        question = question.strip()
        if not question:
            return

        input_widget = self.query_one("#mentor-question-input", Input)
        input_widget.value = ""

        # Mount user message in chat scroll
        chat_scroll = self.query_one("#mentor-chat-scroll", VerticalScroll)
        user_msg = Static(f"👤 **You**:\n{question}", classes="chat-msg chat-user")
        chat_scroll.mount(user_msg)
        chat_scroll.scroll_end(animate=False)

        # Gather repo context
        repo_context = self._get_current_repo_context()

        # Run background worker
        self._ask_mentor_worker(question, repo_context)

    @work(thread=True)
    def _ask_mentor_worker(self, question: str, repo_context: dict[str, Any]) -> None:
        """Fetches mentor answer in background worker thread."""
        overlay = self.query_one(LoadingOverlay)
        self.app.call_from_thread(overlay.show, "Consulting AI Mentor...")
        try:
            res = self.megamind_app.api_client.mentor(
                question=question,
                repo_context=repo_context,
                conversation_id=self._conversation_id,
            )
            answer = res.get("answer", "")
            new_conv_id = res.get("conversation_id")
            if new_conv_id:
                self._conversation_id = new_conv_id

            self.app.call_from_thread(self._append_ai_response, answer)
        except (ApiClientError, GitServiceError) as err:
            self.app.call_from_thread(
                self.megamind_app.show_error, "AI Mentor Error", str(err)
            )
        except Exception as err:  # noqa: BLE001
            self.app.call_from_thread(
                self.megamind_app.show_error, "Unexpected Error", str(err)
            )
        finally:
            self.app.call_from_thread(overlay.hide)

    def _append_ai_response(self, answer: str) -> None:
        """Mounts AI answer container with Markdown widget."""
        chat_scroll = self.query_one("#mentor-chat-scroll", VerticalScroll)
        ai_container = Vertical(
            Label("🤖 MegaMind Mentor:", classes="chat-mentor-label"),
            Markdown(answer),
            classes="chat-msg chat-ai",
        )
        chat_scroll.mount(ai_container)
        chat_scroll.scroll_end(animate=False)

        # Re-focus input
        input_widget = self.query_one("#mentor-question-input", Input)
        input_widget.focus()

    def action_clear_chat(self) -> None:
        """Clears the chat history and resets conversation ID."""
        chat_scroll = self.query_one("#mentor-chat-scroll", VerticalScroll)
        for child in list(chat_scroll.children):
            child.remove()
        chat_scroll.mount(
            Static(
                "Chat history cleared. Start a fresh conversation!",
                classes="chat-msg chat-system",
            )
        )
        self._conversation_id = None
        self.notify("Chat cleared and conversation reset.", title="MEGAMIND")

    def action_refresh_context(self) -> None:
        self.refresh_repo_context()
        self.notify("Mentor repository context refreshed", title="MEGAMIND")

    def action_back_to_dashboard(self) -> None:
        self.app.pop_screen()
