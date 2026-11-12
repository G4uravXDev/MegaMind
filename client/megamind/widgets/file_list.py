"""Reusable file list widget displaying git status entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList
from textual.widgets.option_list import Option


@dataclass(frozen=True)
class FileItem:
    path: str
    category: str  # "staged", "unstaged", "untracked", "conflicted"


class FileList(Widget):
    """OptionList-backed widget listing changed files with status badges."""

    DEFAULT_CSS = """
    FileList {
        width: 100%;
        height: 100%;
        background: $surface;
    }

    FileList OptionList {
        width: 100%;
        height: 100%;
        border: solid $accent;
    }
    """

    class FileHighlighted(Message):
        """Emitted when a file is highlighted in the list."""

        def __init__(self, file_path: str, category: str) -> None:
            super().__init__()
            self.file_path = file_path
            self.category = category

    class FileSelected(Message):
        """Emitted when Enter or Space is pressed on a file."""

        def __init__(self, file_path: str, category: str) -> None:
            super().__init__()
            self.file_path = file_path
            self.category = category

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("space", "toggle_selection", "Toggle", show=False),
    ]

    CATEGORY_BADGES: ClassVar[dict[str, tuple[str, str]]] = {
        "staged": ("STAGED", "green"),
        "unstaged": ("MODIFIED", "yellow"),
        "untracked": ("UNTRACKED", "blue"),
        "conflicted": ("CONFLICT", "bold red"),
    }

    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id)
        self._items: list[FileItem] = []

    def compose(self) -> ComposeResult:
        yield OptionList(id="file-options")

    def set_files(
        self,
        staged: list[str] | None = None,
        unstaged: list[str] | None = None,
        untracked: list[str] | None = None,
        conflicted: list[str] | None = None,
    ) -> None:
        """Populates the list with categorized files."""
        self._items.clear()
        options: list[Option] = []

        categories = [
            ("conflicted", conflicted or []),
            ("staged", staged or []),
            ("unstaged", unstaged or []),
            ("untracked", untracked or []),
        ]

        for cat, files in categories:
            badge_text, style = self.CATEGORY_BADGES[cat]
            for f in files:
                self._items.append(FileItem(path=f, category=cat))
                label = Text()
                label.append(f"[{badge_text:^10}] ", style=f"bold {style}")
                label.append(f, style="bold white")
                options.append(Option(label, id=f"{cat}:{f}"))

        option_list = self.query_one("#file-options", OptionList)
        prev_idx = option_list.highlighted or 0
        option_list.clear_options()
        if options:
            option_list.add_options(options)
            option_list.highlighted = min(prev_idx, len(options) - 1)
        else:
            empty_text = Text("  ✔ Working tree clean", style="italic dim green")
            option_list.add_option(Option(empty_text, disabled=True))

    def get_selected_item(self) -> FileItem | None:
        """Returns currently highlighted file item if any."""
        option_list = self.query_one("#file-options", OptionList)
        idx = option_list.highlighted
        if idx is not None and 0 <= idx < len(self._items):
            return self._items[idx]
        return None

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if 0 <= event.option_index < len(self._items):
            item = self._items[event.option_index]
            self.post_message(self.FileHighlighted(item.path, item.category))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if 0 <= event.option_index < len(self._items):
            item = self._items[event.option_index]
            self.post_message(self.FileSelected(item.path, item.category))

    def action_toggle_selection(self) -> None:
        """Toggles selection on Space press."""
        item = self.get_selected_item()
        if item is not None:
            self.post_message(self.FileSelected(item.path, item.category))
