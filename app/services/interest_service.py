"""Interest extraction service - business logic for extracting interests from prompts."""

from __future__ import annotations

from app.llm.client import LLMClient, LLMServiceError
from app.llm.schemas import InterestExtractionResult


class InterestExtractionError(Exception):
    """Base error for interest extraction failures."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


async def extract_interests_from_prompt(
    prompt: str, llm_client: LLMClient
) -> InterestExtractionResult:
    """Extract interests from a natural language prompt using LLM.

    Returns:
        InterestExtractionResult with add_interests and remove_interests.

    Raises:
        InterestExtractionError: When the LLM layer fails (unavailable, auth, invalid response).
    """
    try:
        return await llm_client.extract_interests(prompt)
    except LLMServiceError as exc:
        raise InterestExtractionError(str(exc), exc.error_code) from exc
