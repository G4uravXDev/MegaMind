"""Configuration settings for the ZIT client."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    api_url: str = os.getenv("ZIT_API_URL", "http://127.0.0.1:8000").rstrip("/")
    token: str = os.getenv("ZIT_TOKEN", "")
    max_diff_chars: int = 20_000
    repo_path: Path = field(default_factory=Path.cwd)

    @property
    def mock(self) -> bool:
        """Returns True if mock mode is active via ZIT_MOCK env var."""
        return os.getenv("ZIT_MOCK", "0").lower() in ("1", "true", "yes")


config = Config()
