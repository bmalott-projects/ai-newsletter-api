from __future__ import annotations
from abc import ABC, abstractmethod
import json
import logging

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.core.config import settings
from app.llm.prompts import (
    INTEREST_EXTRACTION_SYSTEM_PROMPT,
    get_interest_extraction_prompt,
)
from app.llm.schemas import InterestExtractionResult


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def extract_interests(self, prompt: str) -> InterestExtractionResult:
        """Extract interests from a natural language prompt."""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI implementation of LLM client."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    async def extract_interests(self, prompt: str) -> InterestExtractionResult:
        """Extract interests from a natural language prompt using OpenAI."""
        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": INTEREST_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": get_interest_extraction_prompt(prompt)},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent extraction
            )

            # Extract JSON from response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")

            # Parse and validate with Pydantic
            parsed = json.loads(content)
            return InterestExtractionResult(**parsed)

        except Exception as e:
            # Log error and re-raise with context
            logging.error(f"LLM failed to extract interests from prompt: {prompt}. Error: {e}")
            raise RuntimeError(f"Failed to extract interests from LLM: {e}") from e
