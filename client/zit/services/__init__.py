"""Services package for ZIT client."""

from __future__ import annotations

from zit.services.api_client import ApiClient
from zit.services.exceptions import (
    ApiAuthError,
    ApiClientError,
    ApiConnectionError,
    DestructiveActionError,
    GitServiceError,
    RepoNotFoundError,
    ZitError,
)
from zit.services.git_service import (
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
    "RepoHealth",
    "RepoNotFoundError",
    "ZitError",
]
