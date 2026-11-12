"""Amazon Bedrock client wrapper for invoking foundation models via Converse API."""

from __future__ import annotations

import os
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError


class BedrockClientError(Exception):
    """Base error for Bedrock client failures with stable external code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# Action inference configurations
ACTION_CONFIGS: dict[str, dict[str, Any]] = {
    "commit_message": {"maxTokens": 256, "temperature": 0.2},
    "resolve_conflict": {"maxTokens": 2048, "temperature": 0.1},
    "mentor": {"maxTokens": 1024, "temperature": 0.4},
    "coverage": {"maxTokens": 2048, "temperature": 0.2},
}

THROTTLING_ERROR_CODES = {
    "ThrottlingException",
    "TooManyRequestsException",
    "RequestLimitExceeded",
    "ModelNotReadyException",
}


class BedrockClient:
    """Interacts with Amazon Bedrock via the Converse API with retries and clean error mapping."""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            # Region is inherited from the AWS Lambda runtime environment automatically
            self._client = boto3.client("bedrock-runtime")
        return self._client

    def get_model_id(self) -> str:
        """Retrieves the Bedrock model ID from the environment."""
        model_id = os.getenv("BEDROCK_MODEL_ID")
        if not model_id:
            raise BedrockClientError(
                code="CONFIGURATION_ERROR",
                message="BEDROCK_MODEL_ID environment variable is not configured.",
            )
        return model_id

    def converse(
        self,
        action: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
    ) -> str:
        """Invokes Bedrock Converse API with action-specific inference settings and retry."""
        model_id = self.get_model_id()
        config = ACTION_CONFIGS.get(action, {"maxTokens": 1024, "temperature": 0.2})

        system = [{"text": system_prompt}] if system_prompt else []
        inference_config = {
            "maxTokens": config["maxTokens"],
            "temperature": config["temperature"],
        }

        # Attempt invocation with one retry on throttling
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.converse(
                    modelId=model_id,
                    system=system,
                    messages=messages,
                    inferenceConfig=inference_config,
                )
                output_message = response.get("output", {}).get("message", {})
                content_blocks = output_message.get("content", [])
                return "".join(
                    block.get("text", "") for block in content_blocks if "text" in block
                )

            except ClientError as err:
                error_code = err.response.get("Error", {}).get("Code", "Unknown")

                if error_code in THROTTLING_ERROR_CODES:
                    if attempt < max_attempts:
                        time.sleep(1.0)
                        continue
                    raise BedrockClientError(
                        code="THROTTLED",
                        message="Request was throttled by the AI model provider. Please try again shortly.",
                    ) from None

                if error_code in ("AccessDeniedException", "UnauthorizedException"):
                    raise BedrockClientError(
                        code="ACCESS_DENIED",
                        message="Access to the requested AI model was denied. Please verify AWS IAM permissions.",
                    ) from None

                if error_code in ("ValidationException", "ModelNotSupportedException"):
                    raise BedrockClientError(
                        code="VALIDATION_ERROR",
                        message="Invalid request parameters sent to AI model.",
                    ) from None

                if error_code in ("ResourceNotFoundException", "ModelErrorException"):
                    raise BedrockClientError(
                        code="MODEL_ERROR",
                        message="The configured AI model is unavailable or invalid.",
                    ) from None

                # Fallback for unexpected AWS errors - do not leak internal AWS details
                raise BedrockClientError(
                    code="UPSTREAM_ERROR",
                    message="An error occurred while communicating with the AI model provider.",
                ) from None

            except (ReadTimeoutError, ConnectTimeoutError):
                raise BedrockClientError(
                    code="TIMEOUT",
                    message="AI model request timed out.",
                ) from None

        raise BedrockClientError(
            code="UPSTREAM_ERROR",
            message="Unexpected termination during AI model invocation.",
        )
