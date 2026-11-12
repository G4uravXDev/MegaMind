"""Loading overlay and indicator widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator


class LoadingOverlay(Widget):
    """Semi-transparent overlay with a spinner and descriptive message."""

    DEFAULT_CSS = """
    LoadingOverlay {
        layer: overlay;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.75);
        align: center middle;
        display: none;
    }

    LoadingOverlay.visible {
        display: block;
    }

    #loading-container {
        width: 40;
        height: auto;
        padding: 2;
        background: $panel;
        border: heavy $accent;
        align: center middle;
    }

    #loading-label {
        margin-top: 1;
        text-style: bold;
        color: $text;
        text-align: center;
        width: 100%;
    }
    """

    def __init__(self, message: str = "Working...") -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Middle(), Center(), Vertical(id="loading-container"):
            yield Label(self.message, id="loading-label")

    def show(self, message: str | None = None) -> None:
        """Displays the loading overlay and mounts the animated indicator."""
        if message:
            self.message = message
        label = self.query_one("#loading-label", Label)
        label.update(self.message)
        container = self.query_one("#loading-container", Vertical)
        if not container.query(LoadingIndicator):
            container.mount(LoadingIndicator(), before=label)
        self.add_class("visible")

    def hide(self) -> None:
        """Hides the loading overlay and removes the animated indicator."""
        container = self.query_one("#loading-container", Vertical)
        for ind in container.query(LoadingIndicator):
            ind.remove()
        self.remove_class("visible")
