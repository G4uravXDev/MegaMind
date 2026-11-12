"""Tests for the Lambda handler routing, contracts, and privacy guarantees."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from handler import lambda_handler


def test_invalid_event_shape() -> None:
    res = lambda_handler("not-a-dict")  # type: ignore[arg-type]
    assert res["ok"] is False
    assert res["error"]["code"] == "INVALID_EVENT"


def test_missing_action_or_payload() -> None:
    res = lambda_handler({"action": "commit_message"})
    assert res["ok"] is False
    assert res["error"]["code"] == "INVALID_EVENT"


def test_unknown_action() -> None:
    res = lambda_handler({"action": "do_magic", "payload": {}})
    assert res["ok"] is False
    assert res["error"]["code"] == "UNKNOWN_ACTION"
    assert "Unsupported action" in res["error"]["message"]


def test_missing_required_payload_keys() -> None:
    # commit_message requires 'diff'
    res = lambda_handler({"action": "commit_message", "payload": {}})
    assert res["ok"] is False
    assert res["error"]["code"] == "INVALID_PAYLOAD"
    assert "diff" in res["error"]["message"]

    # resolve_conflict requires 'file_path', 'ours', 'theirs'
    res = lambda_handler(
        {"action": "resolve_conflict", "payload": {"file_path": "a.py"}}
    )
    assert res["ok"] is False
    assert res["error"]["code"] == "INVALID_PAYLOAD"


@patch("handler.BedrockClient")
def test_commit_message_success(mock_bedrock_cls: patch) -> None:
    mock_instance = mock_bedrock_cls.return_value
    mock_instance.converse.return_value = "feat: add user authentication"

    event = {
        "action": "commit_message",
        "payload": {
            "diff": "diff --git a/auth.py b/auth.py\n+def login(): pass",
            "recent_commits": ["chore: setup"],
            "truncated": False,
        },
    }
    res = lambda_handler(event)

    assert res["ok"] is True
    assert res["data"] == {"message": "feat: add user authentication"}
    mock_instance.converse.assert_called_once()


@patch("handler.BedrockClient")
def test_resolve_conflict_success(mock_bedrock_cls: patch) -> None:
    mock_instance = mock_bedrock_cls.return_value
    mock_instance.converse.return_value = (
        '{"resolution": "x = 100", "explanation": "Unified constant"}'
    )

    event = {
        "action": "resolve_conflict",
        "payload": {
            "file_path": "constants.py",
            "ours": "x = 10",
            "theirs": "x = 20",
        },
    }
    res = lambda_handler(event)

    assert res["ok"] is True
    assert res["data"]["resolution"] == "x = 100"
    assert res["data"]["explanation"] == "Unified constant"


@patch("handler.BedrockClient")
def test_resolve_conflict_invalid_model_output(mock_bedrock_cls: patch) -> None:
    mock_instance = mock_bedrock_cls.return_value
    mock_instance.converse.return_value = "Not valid JSON output from model"

    event = {
        "action": "resolve_conflict",
        "payload": {
            "file_path": "constants.py",
            "ours": "x = 10",
            "theirs": "x = 20",
        },
    }
    res = lambda_handler(event)

    assert res["ok"] is False
    assert res["error"]["code"] == "INVALID_MODEL_OUTPUT"


@patch("handler.BedrockClient")
def test_mentor_preserves_conversation_id(mock_bedrock_cls: patch) -> None:
    mock_instance = mock_bedrock_cls.return_value
    mock_instance.converse.return_value = (
        "You can use `git stash` to save local changes."
    )

    event = {
        "action": "mentor",
        "payload": {
            "question": "How do I save uncommitted work?",
            "conversation_id": "session-456",
            "repo_context": {"branch": "main"},
        },
    }
    res = lambda_handler(event)

    assert res["ok"] is True
    assert res["data"]["answer"] == "You can use `git stash` to save local changes."
    assert res["data"]["conversation_id"] == "session-456"


@patch("handler.BedrockClient")
def test_coverage_success(mock_bedrock_cls: patch) -> None:
    mock_instance = mock_bedrock_cls.return_value
    mock_instance.converse.return_value = "def test_it(): assert True"

    event = {
        "action": "coverage",
        "payload": {
            "file_path": "test_service.py",
            "source": "def service(): return 1",
        },
    }
    res = lambda_handler(event)

    assert res["ok"] is True
    assert res["data"] == {"tests": "def test_it(): assert True"}


@patch("handler.BedrockClient")
def test_privacy_no_payload_logged(
    mock_bedrock_cls: patch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Critical privacy assertion: Verifies that sensitive code, diffs, conflict hunks,

    and user questions NEVER appear in the log output.
    """
    secret_diff = "SUPER_SECRET_DIFF_TOKEN_9999"
    secret_question = "WHAT_IS_THE_MASTER_ENCRYPTION_KEY_1234"
    secret_code = "SECRET_SOURCE_CODE_REDACTED_7777"

    mock_instance = mock_bedrock_cls.return_value
    mock_instance.converse.return_value = "Normal response"

    with caplog.at_level(logging.DEBUG, logger="megamind.lambda"):
        # Test 1: Commit message with secret diff
        lambda_handler(
            {
                "action": "commit_message",
                "payload": {"diff": secret_diff},
            }
        )

        # Test 2: Mentor with secret question
        lambda_handler(
            {
                "action": "mentor",
                "payload": {"question": secret_question},
            }
        )

        # Test 3: Coverage with secret source
        lambda_handler(
            {
                "action": "coverage",
                "payload": {"file_path": "main.py", "source": secret_code},
            }
        )

    captured_logs = caplog.text

    assert secret_diff not in captured_logs
    assert secret_question not in captured_logs
    assert secret_code not in captured_logs

    # Confirm only metadata was logged
    assert "action=commit_message status=success" in captured_logs
    assert "action=mentor status=success" in captured_logs
    assert "action=coverage status=success" in captured_logs
