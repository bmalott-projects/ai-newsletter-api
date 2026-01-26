from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

ERROR_CODE_BY_STATUS: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
}


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    error: str
    message: str
    details: Any | None = None


def error_detail(
    error: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": error, "message": message}
    if details is not None:
        payload["details"] = details
    return payload


def build_http_error(
    status_code: int,
    error: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=error_detail(error=error, message=message, details=details),
        headers=headers,
    )


def _map_status_to_error(status_code: int) -> str:
    return ERROR_CODE_BY_STATUS.get(status_code, "error")


def _status_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Error"


def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        payload = error_detail(
            error=_map_status_to_error(HTTP_500_INTERNAL_SERVER_ERROR),
            message=_status_phrase(HTTP_500_INTERNAL_SERVER_ERROR),
        )
        return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=payload)
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail and "message" in detail:
        payload = detail
    else:
        payload = error_detail(
            error=_map_status_to_error(exc.status_code),
            message=str(detail) if detail else _status_phrase(exc.status_code),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers=getattr(exc, "headers", None),
    )


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.exception("Unhandled exception", exc_info=exc)
    payload = error_detail(
        error=_map_status_to_error(HTTP_500_INTERNAL_SERVER_ERROR),
        message=_status_phrase(HTTP_500_INTERNAL_SERVER_ERROR),
    )
    return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


def request_validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        payload = error_detail(
            error=_map_status_to_error(HTTP_500_INTERNAL_SERVER_ERROR),
            message=_status_phrase(HTTP_500_INTERNAL_SERVER_ERROR),
        )
        return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=payload)

    payload = error_detail(
        error=_map_status_to_error(422),
        message="Request validation failed",
        details=exc.errors(),
    )
    return JSONResponse(status_code=422, content=payload)
