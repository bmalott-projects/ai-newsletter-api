from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.api.schemas.interests import InterestExtractionRequest
from app.core.auth import get_current_user
from app.core.errors import ErrorResponse, build_http_error
from app.core.prompt_sanitizer import PromptValidationError, sanitize_prompt
from app.core.rate_limit import (
    INTEREST_EXTRACT_RATE_LIMIT,
    limit,
    rate_limit_user_or_ip_key,
)
from app.db.models.user import User
from app.llm.client import (
    LLMAuthenticationError,
    LLMClient,
    LLMInvalidResponseError,
    LLMServiceError,
    LLMUnavailableError,
    OpenAIClient,
)
from app.llm.schemas import InterestExtractionResult
from app.services.interest_service import extract_interests_from_prompt

router = APIRouter()


def get_llm_client() -> LLMClient:
    """Dependency to get LLM client instance."""
    return OpenAIClient()


@router.post(
    "/extract",
    summary="Extract interests to add/remove",
    description="Analyze a prompt and return interests to add or remove.",
    response_model=InterestExtractionResult,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid prompt",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_prompt": {
                            "summary": "Prompt rejected",
                            "value": {
                                "error": "invalid_prompt",
                                "message": "Prompt contains disallowed instruction patterns.",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing or invalid token",
            "content": {
                "application/json": {
                    "examples": {
                        "unauthorized": {
                            "summary": "Unauthorized",
                            "value": {
                                "error": "unauthorized",
                                "message": "Could not validate credentials",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid request body",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "Request validation failed",
                            "value": {
                                "error": "validation_error",
                                "message": "Request validation failed",
                                "details": [
                                    {
                                        "loc": ["body", "prompt"],
                                        "msg": "String should have at least 1 character",
                                        "type": "string_too_short",
                                    }
                                ],
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limited": {
                            "summary": "Too many requests",
                            "value": {
                                "error": "rate_limited",
                                "message": "Too many requests",
                            },
                        }
                    }
                }
            },
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "LLM authentication or response error",
            "content": {
                "application/json": {
                    "examples": {
                        "llm_auth_failed": {
                            "summary": "LLM auth failed",
                            "value": {
                                "error": "llm_auth_failed",
                                "message": "LLM authentication failed.",
                            },
                        },
                        "llm_response_invalid": {
                            "summary": "LLM response invalid",
                            "value": {
                                "error": "llm_response_invalid",
                                "message": "LLM response did not match expected format.",
                            },
                        },
                    }
                }
            },
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "LLM unavailable",
            "content": {
                "application/json": {
                    "examples": {
                        "llm_unavailable": {
                            "summary": "LLM unavailable",
                            "value": {
                                "error": "llm_unavailable",
                                "message": "LLM service error. Try again later.",
                            },
                        }
                    }
                }
            },
        },
    },
)
@limit(INTEREST_EXTRACT_RATE_LIMIT, key_func=rate_limit_user_or_ip_key)
async def extract_interests(
    request: Request,
    request_data: InterestExtractionRequest,
    _current_user: User = Depends(get_current_user),
    llm_client: LLMClient = Depends(get_llm_client),
) -> InterestExtractionResult:
    """Extract interests from a natural language prompt."""
    try:
        sanitized_prompt = sanitize_prompt(request_data.prompt)
        return await extract_interests_from_prompt(sanitized_prompt, llm_client)
    except PromptValidationError as exc:
        raise build_http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error=exc.error_code,
            message=str(exc),
        ) from exc
    except LLMServiceError as exc:
        if isinstance(exc, (LLMAuthenticationError, LLMInvalidResponseError)):
            status_code = status.HTTP_502_BAD_GATEWAY
        elif isinstance(exc, LLMUnavailableError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        raise build_http_error(
            status_code=status_code,
            error=exc.error_code,
            message=str(exc),
        ) from exc
