"""Services package for MEGAMIND client."""

from __future__ import annotations

from megamind.services.api_client import ApiClient
from megamind.services.exceptions import (
    ApiAuthError,
    ApiClientError,
    ApiConnectionError,
    DestructiveActionError,
    GitServiceError,
    MegaMindError,
    RepoNotFoundError,
)
from megamind.services.git_service import (
    BranchInfo,
    CommitDetails,
    CommitFileChange,
    CommitInfo,
    GitService,
    LogGraphEntry,
    RepoHealth,
)

__all__ = [
    "ApiAuthError",
    "ApiClient",
    "ApiClientError",
    "ApiConnectionError",
    "BranchInfo",
    "CommitDetails",
    "CommitFileChange",
    "CommitInfo",
    "DestructiveActionError",
    "GitService",
    "GitServiceError",
    "LogGraphEntry",
    "MegaMindError",
    "RepoHealth",
    "RepoNotFoundError",
]
