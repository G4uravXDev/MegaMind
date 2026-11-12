"""Screens package for MEGAMIND client."""

from __future__ import annotations

from megamind.screens.branches import BranchesScreen
from megamind.screens.commit import CommitScreen
from megamind.screens.dashboard import DashboardScreen
from megamind.screens.log_graph import LogGraphScreen
from megamind.screens.staging import StagingScreen

__all__ = [
    "BranchesScreen",
    "CommitScreen",
    "DashboardScreen",
    "LogGraphScreen",
    "StagingScreen",
]
