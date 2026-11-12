"""Custom exceptions for MEGAMIND client."""

from __future__ import annotations


class MegaMindError(Exception):
    """Base exception for all MEGAMIND client errors."""


class GitServiceError(MegaMindError):
    """Exception raised for errors during Git operations."""


class RepoNotFoundError(GitServiceError):
    """Exception raised when the directory is not a Git repository."""


class DestructiveActionError(GitServiceError):
    """Exception raised when a destructive action fails or is refused."""


class ApiClientError(MegaMindError):
    """Exception raised for errors during backend API calls."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiConnectionError(ApiClientError):
    """Exception raised when unable to connect to the backend API."""


class ApiAuthError(ApiClientError):
    """Exception raised for authentication or permission failures."""
