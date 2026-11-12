"""Pytest fixtures and configuration for Lambda tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Add lambda directory to sys.path so modules (handler, bedrock_client, prompts) can be imported directly
LAMBDA_DIR = Path(__file__).resolve().parent.parent
if str(LAMBDA_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA_DIR))
