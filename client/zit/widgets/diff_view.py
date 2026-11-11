"""Rich-colored diff viewer widget with line numbering."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static


class DiffView(Widget):
    """Displays a git diff with line numbers and syntax highlighting."""

    DEFAULT_CSS = """
    DiffView {
        width: 100%;
        height: 100%;
        background: $surface;
        border: solid $primary;
    }

    #diff-scroll {
        width: 100%;
        height: 100%;
    }

    #diff-content {
        width: auto;
        min-width: 100%;
        padding: 0 1;
    }
    """

    def __init__(self, diff_text: str = "", id: str | None = None) -> None:
        super().__init__(id=id)
        self._diff_text = diff_text

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="diff-scroll"):
            yield Static(id="diff-content")

    def on_mount(self) -> None:
        self.update_diff(self._diff_text)

    def update_diff(self, diff_text: str) -> None:
        """Parses and renders formatted diff text."""
        self._diff_text = diff_text
        static = self.query_one("#diff-content", Static)
        if not diff_text.strip():
            static.update(Text("No changes / empty diff", style="dim italic"))
            return

        rich_text = self._format_diff(diff_text)
        static.update(rich_text)

    def _format_diff(self, diff: str) -> Text:
        """Formats unified diff with line numbers and add/delete colors."""
        rich_text = Text()
        old_lineno = 0
        new_lineno = 0
        in_hunk = False

        for line in diff.splitlines():
            if line.startswith(("diff --git", "index ")):
                rich_text.append(f"{line}\n", style="bold yellow")
            elif line.startswith(("--- ", "+++ ")):
                rich_text.append(f"{line}\n", style="bold magenta")
            elif line.startswith("@@"):
                in_hunk = True
                # Parse hunk header: @@ -start,len +start,len @@
                rich_text.append(f"{line}\n", style="bold cyan")
                try:
                    parts = line.split("@@")[1].strip().split()
                    old_part = parts[0].lstrip("-")
                    new_part = parts[1].lstrip("+")
                    old_lineno = int(old_part.split(",")[0])
                    new_lineno = int(new_part.split(",")[0])
                except (IndexError, ValueError):
                    old_lineno, new_lineno = 0, 0
            elif in_hunk and line.startswith("+"):
                prefix = f"     {new_lineno:4d} │ " if new_lineno else "      + │ "
                rich_text.append(prefix, style="dim green")
                rich_text.append(f"{line}\n", style="bold green")
                new_lineno += 1
            elif in_hunk and line.startswith("-"):
                prefix = f"{old_lineno:4d}      │ " if old_lineno else "      - │ "
                rich_text.append(prefix, style="dim red")
                rich_text.append(f"{line}\n", style="bold red")
                old_lineno += 1
            elif in_hunk:
                prefix = (
                    f"{old_lineno:4d} {new_lineno:4d} │ "
                    if old_lineno and new_lineno
                    else "        │ "
                )
                rich_text.append(prefix, style="dim")
                rich_text.append(f"{line}\n", style="white")
                if old_lineno:
                    old_lineno += 1
                if new_lineno:
                    new_lineno += 1
            else:
                rich_text.append(f"{line}\n", style="white")

        return rich_text
