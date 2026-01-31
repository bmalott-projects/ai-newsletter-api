from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InterestExtractionResult(BaseModel):
    """Structured output from LLM for interest extraction."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "add_interests": ["AI", "startups"],
                    "remove_interests": ["crypto", "NFTs"],
                }
            ]
        }
    )

    add_interests: list[str] = Field(
        default_factory=list,
        description="List of interests to add based on the user's prompt",
        examples=[["AI", "startups"]],
    )
    remove_interests: list[str] = Field(
        default_factory=list,
        description="List of interests to remove based on the user's prompt",
        examples=[["crypto", "NFTs"]],
    )
