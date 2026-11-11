"""Screens package for ZIT client."""

from __future__ import annotations

from zit.screens.branches import BranchesScreen
from zit.screens.commit import CommitScreen
from zit.screens.dashboard import DashboardScreen
from zit.screens.log_graph import LogGraphScreen
from zit.screens.staging import StagingScreen

__all__ = [
    "BranchesScreen",
    "CommitScreen",
    "DashboardScreen",
    "LogGraphScreen",
    "StagingScreen",
]
