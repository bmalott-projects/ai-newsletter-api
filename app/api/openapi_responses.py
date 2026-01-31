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


def error_responses(*examples: ErrorExample) -> dict[int, dict[str, Any]]:
    responses: dict[int, dict[str, Any]] = {}
    for example in examples:
        response = responses.get(example.status_code)
        if response is None:
            response = {
                "model": ErrorResponse,
                "description": example.description,
                "content": {"application/json": {"examples": {}}},
            }
            responses[example.status_code] = response

        example_name = example.example_name or example.error
        payload: dict[str, Any] = {
            "error": example.error,
            "message": example.message,
        }
        if example.details is not None:
            payload["details"] = example.details

        response["content"]["application/json"]["examples"][example_name] = {
            "summary": example.summary or example.description,
            "value": payload,
        }

    return responses


def rate_limited_response(description: str = "Rate limit exceeded") -> dict[int, dict[str, Any]]:
    return error_responses(
        ErrorExample(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="rate_limited",
            message="Too many requests",
            description=description,
            summary="Too many requests",
        )
    )


def unauthorized_response(description: str = "Missing or invalid token") -> dict[int, dict[str, Any]]:
    return error_responses(
        ErrorExample(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="unauthorized",
            message="Could not validate credentials",
            description=description,
            summary="Unauthorized",
        )
    )
