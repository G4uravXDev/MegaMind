"""Shared UI widgets for MEGAMIND client."""

from __future__ import annotations

from megamind.widgets.commit_list import CommitList
from megamind.widgets.confirm_dialog import ConfirmDialog
from megamind.widgets.diff_view import DiffView
from megamind.widgets.error_panel import ErrorModal
from megamind.widgets.file_list import FileItem, FileList
from megamind.widgets.input_dialog import InputDialog
from megamind.widgets.loading import LoadingOverlay

__all__ = [
    "CommitList",
    "ConfirmDialog",
    "DiffView",
    "ErrorModal",
    "FileItem",
    "FileList",
    "InputDialog",
    "LoadingOverlay",
]
