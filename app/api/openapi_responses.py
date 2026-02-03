from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import status

from app.core.errors import ErrorResponse


@dataclass(frozen=True)
class ErrorExample:
    status_code: int
    error: str
    message: str
    description: str
    summary: str | None = None
    details: Any | None = None
    example_name: str | None = None


def error_responses(*examples: ErrorExample) -> dict[int | str, dict[str, Any]]:
    responses: dict[int | str, dict[str, Any]] = {}
    for example in examples:
        response: dict[str, Any] | None = responses.get(example.status_code)
        if response is None:
            examples_payload: dict[str, dict[str, Any]] = {}
            content: dict[str, dict[str, dict[str, Any]]] = {
                "application/json": {"examples": examples_payload}
            }
            response = {
                "model": ErrorResponse,
                "description": example.description,
                "content": content,
            }
            responses[example.status_code] = response
        assert response is not None

        example_name = example.example_name or example.error
        payload: dict[str, Any] = {
            "error": example.error,
            "message": example.message,
        }
        if example.details is not None:
            payload["details"] = example.details

        example_entry: dict[str, Any] = {
            "summary": example.summary or example.description,
            "value": payload,
        }
        response_content: dict[str, dict[str, dict[str, Any]]] = response["content"]
        response_content["application/json"]["examples"][example_name] = example_entry

    return responses


def rate_limited_response(
    description: str = "Rate limit exceeded",
) -> dict[int | str, dict[str, Any]]:
    return error_responses(
        ErrorExample(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="rate_limited",
            message="Too many requests",
            description=description,
            summary="Too many requests",
        )
    )


def unauthorized_response(
    description: str = "Missing or invalid token",
) -> dict[int | str, dict[str, Any]]:
    return error_responses(
        ErrorExample(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="unauthorized",
            message="Could not validate credentials",
            description=description,
            summary="Unauthorized",
        )
    )
