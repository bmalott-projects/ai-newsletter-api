from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.schemas.interests import InterestExtractionRequest
from app.core.auth import get_current_user
from app.core.errors import build_http_error
from app.db.models.user import User
from app.llm.client import LLMClient, LLMServiceError, OpenAIClient
from app.llm.schemas import InterestExtractionResult
from app.services.interest import extract_interests_from_prompt

router = APIRouter()


def get_llm_client() -> LLMClient:
    """Dependency to get LLM client instance."""
    return OpenAIClient()


@router.post(
    "/extract",
    response_model=InterestExtractionResult,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
async def extract_interests(
    request: InterestExtractionRequest,
    _current_user: User = Depends(get_current_user),
    llm_client: LLMClient = Depends(get_llm_client),
) -> InterestExtractionResult:
    """Extract interests from a natural language prompt."""
    try:
        return await extract_interests_from_prompt(request.prompt, llm_client)
    except LLMServiceError as exc:
        raise build_http_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error=exc.error_code,
            message=str(exc),
        ) from exc
