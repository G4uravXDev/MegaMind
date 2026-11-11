"""Reusable modal text input dialog."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class InputDialog(ModalScreen[str | None]):
    """Modal dialog prompting the user for text input."""

    DEFAULT_CSS = """
    InputDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #input-dialog-box {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }

    #input-dialog-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        content-align: center middle;
        width: 100%;
    }

    #input-dialog-prompt {
        margin-bottom: 1;
        color: $text;
    }

    #dialog-text-input {
        margin-bottom: 1;
    }

    #input-dialog-buttons {
        grid-size: 2;
        grid-gutter: 2;
        height: 3;
        margin-top: 1;
    }

    #input-dialog-buttons Button {
        width: 100%;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(
        self,
        title: str,
        prompt: str,
        initial_value: str = "",
        placeholder: str = "",
        confirm_label: str = "Submit",
    ) -> None:
        super().__init__()
        self.dialog_title = title
        self.prompt = prompt
        self.initial_value = initial_value
        self.placeholder = placeholder
        self.confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(id="input-dialog-box"):
            yield Label(self.dialog_title, id="input-dialog-title")
            yield Label(self.prompt, id="input-dialog-prompt")
            yield Input(
                value=self.initial_value,
                placeholder=self.placeholder,
                id="dialog-text-input",
            )
            with Grid(id="input-dialog-buttons"):
                yield Button("Cancel [Esc]", variant="default", id="btn-input-cancel")
                yield Button(
                    f"{self.confirm_label} [Enter]",
                    variant="primary",
                    id="btn-input-confirm",
                )

    def on_mount(self) -> None:
        input_widget = self.query_one("#dialog-text-input", Input)
        input_widget.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-input-confirm":
            input_widget = self.query_one("#dialog-text-input", Input)
            self._submit(input_widget.value)
        else:
            self.dismiss(None)

    def _submit(self, val: str) -> None:
        val = val.strip()
        self.dismiss(val if val else None)

    def action_cancel(self) -> None:
        self.dismiss(None)
