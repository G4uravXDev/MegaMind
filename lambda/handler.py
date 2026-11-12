"""AWS Lambda handler for MegaMind AI actions."""

from __future__ import annotations

import logging
import time
from typing import Any

from bedrock_client import BedrockClient, BedrockClientError
from prompts import commit, conflict, coverage, mentor
from prompts.conflict import InvalidModelOutputError

# Configure minimal logger ensuring no sensitive data is leaked
logger = logging.getLogger("megamind.lambda")
logger.setLevel(logging.INFO)

SUPPORTED_ACTIONS = {
    "commit_message": {
        "required_keys": ["diff"],
        "builder": commit.build_messages,
        "parser": commit.parse_response,
    },
    "resolve_conflict": {
        "required_keys": ["file_path", "ours", "theirs"],
        "builder": conflict.build_messages,
        "parser": conflict.parse_response,
    },
    "mentor": {
        "required_keys": ["question"],
        "builder": mentor.build_messages,
        "parser": mentor.parse_response,
    },
    "coverage": {
        "required_keys": ["file_path", "source"],
        "builder": coverage.build_messages,
        "parser": coverage.parse_response,
    },
}


def _error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _success_response(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "data": data,
    }


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Main Lambda entry point.

    Validates payload shape, routes to the appropriate prompt handler, invokes
    Amazon Bedrock via Converse API, and formats the response contract.
    Never logs sensitive data (diffs, code, conflict contents, or user queries).
    Never raises an unhandled exception to the caller.
    """
    start_time = time.perf_counter()
    action = "unknown"

    try:
        # Validate event structure
        if not isinstance(event, dict):
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(
                "action=%s status=error code=INVALID_EVENT latency_ms=%d",
                action,
                latency_ms,
            )
            return _error_response(
                "INVALID_EVENT", "Event payload must be a JSON object."
            )

        action = str(event.get("action", ""))
        payload = event.get("payload")

        if not action or payload is None or not isinstance(payload, dict):
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(
                "action=%s status=error code=INVALID_EVENT latency_ms=%d",
                action,
                latency_ms,
            )
            return _error_response(
                "INVALID_EVENT", "Event must contain 'action' and 'payload' dictionary."
            )

        # Validate action
        if action not in SUPPORTED_ACTIONS:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(
                "action=%s status=error code=UNKNOWN_ACTION latency_ms=%d",
                action,
                latency_ms,
            )
            return _error_response("UNKNOWN_ACTION", f"Unsupported action '{action}'.")

        handler_config = SUPPORTED_ACTIONS[action]

        # Validate required payload keys
        for key in handler_config["required_keys"]:
            if key not in payload:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                logger.warning(
                    "action=%s status=error code=INVALID_PAYLOAD latency_ms=%d",
                    action,
                    latency_ms,
                )
                return _error_response(
                    "INVALID_PAYLOAD", f"Missing required payload key '{key}'."
                )

        # Build prompt & messages
        builder = handler_config["builder"]
        parser = handler_config["parser"]
        system_prompt, messages = builder(payload)

        # Invoke Bedrock
        client = BedrockClient()
        raw_text = client.converse(
            action=action,
            system_prompt=system_prompt,
            messages=messages,
        )

        # Parse response into the action contract
        data = parser(raw_text)

        # If mentor action and conversation_id was provided, preserve it in output
        if action == "mentor" and "conversation_id" in payload:
            data["conversation_id"] = payload["conversation_id"]

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info("action=%s status=success latency_ms=%d", action, latency_ms)
        return _success_response(data)

    except BedrockClientError as err:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(
            "action=%s status=error code=%s latency_ms=%d", action, err.code, latency_ms
        )
        return _error_response(err.code, err.message)

    except InvalidModelOutputError as err:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(
            "action=%s status=error code=INVALID_MODEL_OUTPUT latency_ms=%d",
            action,
            latency_ms,
        )
        return _error_response("INVALID_MODEL_OUTPUT", str(err))

    except Exception:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            "action=%s status=error code=INTERNAL_ERROR latency_ms=%d",
            action,
            latency_ms,
        )
        return _error_response(
            "INTERNAL_ERROR", "An internal error occurred while processing the request."
        )
