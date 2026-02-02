from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("add_interests", "remove_interests")
    @classmethod
    def normalize_interests(cls, value: list[str]) -> list[str]:
        """Trim whitespace, drop empty values, and de-duplicate interests."""
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = item.strip()
            if not cleaned:
                continue
            normalized_key = cleaned.casefold()
            if normalized_key in seen:
                continue
            seen.add(normalized_key)
            normalized.append(cleaned)
        return normalized
