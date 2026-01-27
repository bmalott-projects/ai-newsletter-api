from __future__ import annotations

from pydantic import BaseModel, Field


class InterestExtractionRequest(BaseModel):
    """Request model for interest extraction."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language prompt from which a user's interests are extracted",
    )
