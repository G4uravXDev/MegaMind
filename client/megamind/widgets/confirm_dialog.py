"""Reusable confirmation dialog modal for destructive Git actions."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmDialog(ModalScreen[bool]):
    """Modal dialog that warns about lost data and returns True on confirmation."""

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #dialog-box {
        width: 60;
        height: auto;
        border: thick $error;
        background: $panel;
        padding: 1 2;
    }

    #dialog-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
        content-align: center middle;
        width: 100%;
    }

    #dialog-message {
        margin-bottom: 1;
        color: $text;
    }

    #dialog-details {
        margin-bottom: 1;
        padding: 1;
        background: $boost;
        color: $warning;
        border: dashed $warning;
    }

    #dialog-buttons {
        grid-size: 2;
        grid-gutter: 2;
        height: 3;
        margin-top: 1;
    }

    #dialog-buttons Button {
        width: 100%;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("enter", "confirm", "Confirm", priority=True),
    ]

    def __init__(
        self,
        title: str,
        message: str,
        details: str | None = None,
        confirm_label: str = "Proceed",
    ) -> None:
        super().__init__()
        self.dialog_title = title
        self.message = message
        self.details = details
        self.confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-box"):
            yield Label(f"⚠️  {self.dialog_title}", id="dialog-title")
            yield Static(self.message, id="dialog-message")
            if self.details:
                yield Static(
                    f"Warning - The following will be permanently lost:\n{self.details}",
                    id="dialog-details",
                )
            with Grid(id="dialog-buttons"):
                yield Button("Cancel [Esc]", variant="default", id="btn-cancel")
                yield Button(
                    f"{self.confirm_label} [Enter]",
                    variant="error",
                    id="btn-confirm",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
