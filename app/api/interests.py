from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

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


class InterestExtractionRequest(BaseModel):
    """Request model for interest extraction."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language prompt to extract interests from",
    )


@router.post("/extract", response_model=InterestExtractionResult)
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
