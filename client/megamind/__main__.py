"""CLI entry point for MEGAMIND assistant."""

from __future__ import annotations

import sys
from pathlib import Path

from megamind.app import MegaMindApp


def main() -> int:
    """Runs the MEGAMIND terminal application."""
    repo_path = Path.cwd()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        repo_path = Path(sys.argv[1])

    app = MegaMindApp(repo_path=repo_path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
