"""Dismissible error modal to prevent application crashes."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ErrorModal(ModalScreen[None]):
    """Modal screen displaying an error message cleanly."""

    DEFAULT_CSS = """
    ErrorModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #error-box {
        width: 65;
        height: auto;
        border: thick $error;
        background: $panel;
        padding: 1 2;
    }

    #error-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
        content-align: center middle;
        width: 100%;
    }

    #error-message {
        margin-bottom: 1;
        color: $text;
        max-height: 15;
        overflow-y: auto;
    }

    #error-button {
        width: 100%;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "dismiss_modal", "Dismiss", priority=True),
        Binding("enter", "dismiss_modal", "Dismiss", priority=True),
        Binding("space", "dismiss_modal", "Dismiss", priority=True),
    ]

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self.error_title = title
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="error-box"):
            yield Label(f"❌  {self.error_title}", id="error-title")
            yield Static(self.message, id="error-message")
            yield Button("Dismiss [Esc / Enter]", variant="error", id="error-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_dismiss_modal(self) -> None:
        self.dismiss()
