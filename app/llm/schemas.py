from __future__ import annotations

from pydantic import BaseModel, Field


class InterestExtractionResult(BaseModel):
    """Structured output from LLM for interest extraction."""

    add_interests: list[str] = Field(
        default_factory=list,
        description="List of interests to add based on the user's prompt",
    )
    remove_interests: list[str] = Field(
        default_factory=list,
        description="List of interests to remove based on the user's prompt",
    )
