"""Help overlay modal listing all ZIT keybindings and workflows."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HelpModal(ModalScreen[None]):
    """Modal cheatsheet of global and screen-specific keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }

    #help-box {
        width: 80%;
        height: 80%;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }

    #help-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        content-align: center middle;
        width: 100%;
    }

    #help-scroll {
        height: 1fr;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }

    .help-section-title {
        text-style: bold;
        color: $warning;
        margin-top: 1;
        margin-bottom: 0;
    }

    .help-entry {
        color: $text;
        margin-left: 2;
    }

    #help-buttons {
        height: 3;
        margin-top: 1;
        align-horizontal: center;
    }

    #help-buttons Button {
        width: 24;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close", "Close", priority=True),
        Binding("question_mark", "close", "Close", show=False, priority=True),
        Binding("?", "close", "Close", show=False, priority=True),
    ]

    HELP_TEXT = """
[bold cyan]Global Keybindings[/bold cyan]
  [bold yellow]? / F1[/bold yellow]       Toggle this Help overlay
  [bold yellow]Esc[/bold yellow]          Return to Dashboard / dismiss modal
  [bold yellow]r[/bold yellow]            Refresh current screen data
  [bold yellow]q[/bold yellow]            Quit ZIT

[bold cyan]1. Dashboard Screen (Default)[/bold cyan]
  [bold yellow]s[/bold yellow]            Go to Staging view
  [bold yellow]c[/bold yellow]            Go to Commit view
  [bold yellow]b[/bold yellow]            Go to Branches view
  [bold yellow]l[/bold yellow]            Go to Log Graph view
  [bold yellow]t[/bold yellow]            Go to Time Travel (stash, reset, recovery)
  [bold yellow]m[/bold yellow]            Go to Merge Conflicts view (when conflicts exist)
  [bold yellow]a[/bold yellow]            Open AI Mentor chat
  [bold yellow]v[/bold yellow]            Generate AI unit test coverage for highlighted file

[bold cyan]2. Staging Screen (s)[/bold cyan]
  [bold yellow]Enter / Space[/bold yellow] Toggle stage / unstage for selected file
  [bold yellow]a[/bold yellow]            Stage ALL changes (-A)
  [bold yellow]u[/bold yellow]            Unstage ALL changes
  [bold yellow]d[/bold yellow]            Discard uncommitted changes (destructive, with confirmation)
  [bold yellow]c[/bold yellow]            Proceed directly to Commit screen
  [bold yellow]v[/bold yellow]            Generate AI unit test coverage for selected file

[bold cyan]3. Commit Screen (c)[/bold cyan]
  [bold yellow]g[/bold yellow]            Generate AI commit message from staged diff & history
  [bold yellow]Ctrl+S[/bold yellow]       Create commit with current message (validates staged & non-empty)
  [bold yellow]s[/bold yellow]            Return to Staging view

[bold cyan]4. Branches Screen (b)[/bold cyan]
  [bold yellow]Enter[/bold yellow]        Switch to highlighted branch (guards uncommitted changes)
  [bold yellow]n[/bold yellow]            Create a new branch from HEAD
  [bold yellow]r[/bold yellow]            Rename selected branch
  [bold yellow]d[/bold yellow]            Delete selected branch (with confirmation; refuses current branch)

[bold cyan]5. Log Graph Screen (l)[/bold cyan]
  [bold yellow]↑ / ↓[/bold yellow]        Browse visual commit graph across all branches
  [bold yellow]Enter[/bold yellow]        Inspect full commit message, author, date, and changed files (+/- lines)

[bold cyan]6. Time Travel Screen (t)[/bold cyan]
  [bold yellow]1[/bold yellow]            Stash Tab:
                 [bold yellow]s[/bold yellow] Save stash with a custom name
                 [bold yellow]a[/bold yellow] Apply selected stash (keep in list)
                 [bold yellow]p[/bold yellow] Pop selected stash (apply & remove)
                 [bold yellow]d[/bold yellow] Drop selected stash (destructive confirmation)
  [bold yellow]2[/bold yellow]            Reset Tab:
                 Choose Soft, Mixed, or Hard reset with explicit safety warnings
  [bold yellow]3[/bold yellow]            Recovery Tab (Reflog):
                 Inspect reflog entries; press [bold yellow]Enter[/bold yellow] to restore HEAD

[bold cyan]7. Merge Conflicts Screen (m)[/bold cyan]
  [bold yellow]Shift+G[/bold yellow]      Request AI resolution for active conflict hunk
  [bold yellow]m[/bold yellow]            Apply center panel suggestion/edit to active hunk
  [bold yellow]n / p[/bold yellow]        Navigate to Next / Previous hunk
  Auto-writes file and stages it when all hunks are resolved!

[bold cyan]8. AI Mentor Chat (a)[/bold cyan]
  Type a plain-English Git question and press [bold yellow]Enter[/bold yellow] to ask the AI.
  Live repository context (branch, changes count, commits) is automatically included.
  [bold yellow]c[/bold yellow]            Clear chat history and reset conversation context
"""

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Label("💡 ZIT Quick Reference & Shortcuts", id="help-title")
            with VerticalScroll(id="help-scroll"):
                yield Static(self.HELP_TEXT)
            with Grid(id="help-buttons"):
                yield Button("Close [Esc]", variant="primary", id="btn-help-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
