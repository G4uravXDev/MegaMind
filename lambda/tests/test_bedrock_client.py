"""Tests for the Bedrock Converse API client wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from bedrock_client import BedrockClient, BedrockClientError
from botocore.exceptions import ClientError, ReadTimeoutError


def test_missing_model_id_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    client = BedrockClient()
    with pytest.raises(BedrockClientError) as exc_info:
        client.converse(
            "commit_message", "system", [{"role": "user", "content": [{"text": "hi"}]}]
        )

    assert exc_info.value.code == "CONFIGURATION_ERROR"
    assert "BEDROCK_MODEL_ID" in exc_info.value.message


def test_successful_converse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
    mock_boto = MagicMock()
    mock_boto.converse.return_value = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "feat: successful commit"}],
            }
        }
    }

    client = BedrockClient(client=mock_boto)
    res = client.converse(
        "commit_message",
        "sys prompt",
        [{"role": "user", "content": [{"text": "diff"}]}],
    )

    assert res == "feat: successful commit"
    mock_boto.converse.assert_called_once()
    call_kwargs = mock_boto.converse.call_args[1]
    assert call_kwargs["modelId"] == "anthropic.claude-v2"
    assert call_kwargs["inferenceConfig"]["maxTokens"] == 256
    assert call_kwargs["inferenceConfig"]["temperature"] == 0.2


def test_throttling_retry_and_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
    mock_boto = MagicMock()

    throttle_err = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "Converse",
    )
    success_resp = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "resolved"}],
            }
        }
    }
    # Fail first attempt with throttle, succeed on second
    mock_boto.converse.side_effect = [throttle_err, success_resp]

    client = BedrockClient(client=mock_boto)
    with patch("time.sleep", return_value=None) as mock_sleep:
        res = client.converse("resolve_conflict", "sys", [])
        assert res == "resolved"
        assert mock_boto.converse.call_count == 2
        mock_sleep.assert_called_once_with(1.0)


def test_throttling_exhaustion_raises_throttled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
    mock_boto = MagicMock()
    throttle_err = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "Converse",
    )
    mock_boto.converse.side_effect = [throttle_err, throttle_err]

    client = BedrockClient(client=mock_boto)
    with patch("time.sleep", return_value=None):
        with pytest.raises(BedrockClientError) as exc_info:
            client.converse("mentor", "sys", [])

        assert exc_info.value.code == "THROTTLED"
        assert "throttled" in exc_info.value.message.lower()


def test_access_denied_error_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
    mock_boto = MagicMock()
    err = ClientError(
        {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "User arn:aws:iam::123:user/test is not authorized",
            }
        },
        "Converse",
    )
    mock_boto.converse.side_effect = err

    client = BedrockClient(client=mock_boto)
    with pytest.raises(BedrockClientError) as exc_info:
        client.converse("commit_message", "sys", [])

    assert exc_info.value.code == "ACCESS_DENIED"
    # Verify no internal AWS details or ARNs are leaked
    assert "arn:aws" not in exc_info.value.message


def test_validation_error_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
    mock_boto = MagicMock()
    err = ClientError(
        {"Error": {"Code": "ValidationException", "Message": "Invalid parameters"}},
        "Converse",
    )
    mock_boto.converse.side_effect = err

    client = BedrockClient(client=mock_boto)
    with pytest.raises(BedrockClientError) as exc_info:
        client.converse("coverage", "sys", [])

    assert exc_info.value.code == "VALIDATION_ERROR"


def test_timeout_error_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
    mock_boto = MagicMock()
    mock_boto.converse.side_effect = ReadTimeoutError(
        endpoint_url="https://bedrock.aws"
    )

    client = BedrockClient(client=mock_boto)
    with pytest.raises(BedrockClientError) as exc_info:
        client.converse("commit_message", "sys", [])

    assert exc_info.value.code == "TIMEOUT"
