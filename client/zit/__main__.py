"""CLI entry point for ZIT assistant."""

from __future__ import annotations

import sys
from pathlib import Path

from zit.app import ZitApp


def main() -> int:
    """Runs the ZIT terminal application."""
    repo_path = Path.cwd()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        repo_path = Path(sys.argv[1])

    app = ZitApp(repo_path=repo_path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
