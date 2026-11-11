"""Modal dialog displaying AI-generated test coverage with save option."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea

from zit.widgets.input_dialog import InputDialog


class CoverageModal(ModalScreen[None]):
    """Modal displaying generated tests in a read-only viewer with a Save action."""

    DEFAULT_CSS = """
    CoverageModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }

    #coverage-box {
        width: 85%;
        height: 80%;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }

    #coverage-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        width: 100%;
    }

    #coverage-code-view {
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }

    #coverage-buttons {
        grid-size: 2;
        grid-gutter: 2;
        height: 3;
        margin-top: 1;
    }

    #coverage-buttons Button {
        width: 100%;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close", "Close", priority=True),
        Binding("s", "save_file", "Save to File"),
    ]

    def __init__(self, file_path: str, tests: str) -> None:
        super().__init__()
        self.file_path = file_path
        self.tests = tests

    def compose(self) -> ComposeResult:
        with Vertical(id="coverage-box"):
            yield Label(
                f"🧪 AI-Generated Tests for {self.file_path}", id="coverage-title"
            )
            yield TextArea(self.tests, read_only=True, id="coverage-code-view")
            with Grid(id="coverage-buttons"):
                yield Button(
                    "Save to File [s]", variant="primary", id="btn-coverage-save"
                )
                yield Button("Close [Esc]", variant="default", id="btn-coverage-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-coverage-save":
            self.action_save_file()
        else:
            self.action_close()

    def action_save_file(self) -> None:
        """Prompts user for destination path and writes tests to disk."""
        stem = Path(self.file_path).stem
        default_name = f"test_{stem}.py"

        def _on_filename(filename: str | None) -> None:
            if not filename:
                return

            repo_path = getattr(self.app, "repo_path", Path.cwd())
            target = Path(repo_path) / filename
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(self.tests, encoding="utf-8")
                self.notify(f"Tests saved to {filename}", title="ZIT Coverage")
                self.dismiss(None)
            except OSError as err:
                self.notify(
                    f"Failed to save {filename}: {err}",
                    title="Save Error",
                    severity="error",
                )

        self.app.push_screen(
            InputDialog(
                title="Save Generated Tests",
                prompt="Enter file path to save tests:",
                initial_value=default_name,
                placeholder="e.g. tests/test_my_feature.py",
                confirm_label="Save",
            ),
            callback=_on_filename,
        )

    def action_close(self) -> None:
        self.dismiss(None)
