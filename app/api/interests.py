from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.db.models.user import User
from app.llm.client import OpenAIClient
from app.llm.schemas import InterestExtractionResult
from app.services.interest import extract_interests_from_prompt

router = APIRouter()


class InterestExtractionRequest(BaseModel):
    """Request model for interest extraction."""

    prompt: str


@router.post("/extract", response_model=InterestExtractionResult)
async def extract_interests(
    request: InterestExtractionRequest,
    _current_user: User = Depends(get_current_user),
) -> InterestExtractionResult:
    """Extract interests from a natural language prompt."""
    llm_client = OpenAIClient()
    return await extract_interests_from_prompt(request.prompt, llm_client)
