"""Reusable commit list widget for recent commit history."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from zit.services.git_service import CommitInfo


class CommitList(Widget):
    """Displays a list of recent commits with hash, author, and summary."""

    DEFAULT_CSS = """
    CommitList {
        width: 100%;
        height: 100%;
        background: $surface;
    }

    CommitList OptionList {
        width: 100%;
        height: 100%;
        border: solid $primary;
    }
    """

    class CommitSelected(Message):
        """Emitted when a commit is selected with Enter."""

        def __init__(self, commit: CommitInfo) -> None:
            super().__init__()
            self.commit = commit

    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id)
        self._commits: list[CommitInfo] = []

    def compose(self) -> ComposeResult:
        yield OptionList(id="commit-options")

    def set_commits(self, commits: list[CommitInfo]) -> None:
        """Populates the widget with commits."""
        self._commits = list(commits)
        option_list = self.query_one("#commit-options", OptionList)
        option_list.clear_options()

        if not commits:
            empty_text = Text(
                "  (No commits yet in this repository)", style="dim italic"
            )
            option_list.add_option(Option(empty_text, disabled=True))
            return

        options = []
        for c in commits:
            label = Text()
            label.append(f"{c.hash:7s} ", style="bold yellow")
            label.append(f"({c.date}) ", style="dim cyan")
            label.append(f"[{c.author}] ", style="magenta")
            label.append(c.message, style="white")
            options.append(Option(label, id=c.full_hash))

        option_list.add_options(options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if 0 <= event.option_index < len(self._commits):
            commit = self._commits[event.option_index]
            self.post_message(self.CommitSelected(commit))
