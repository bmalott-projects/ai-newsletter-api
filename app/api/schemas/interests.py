from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InterestExtractionRequest(BaseModel):
    """Request model for interest extraction."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prompt": "I want more AI and startup news but less crypto and NFTs."
                }
            ]
        }
    )

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language prompt from which a user's interests are extracted",
        examples=["I want more AI and startup news but less crypto and NFTs."],
    )
