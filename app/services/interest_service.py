"""Interest extraction service - business logic for extracting interests from prompts."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLMClient, LLMServiceError
from app.llm.schemas import InterestExtractionResult


class InterestExtractionError(Exception):
    """Base error for interest extraction failures."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class InterestService:
    """Service for extracting interests from natural language prompts via LLM."""

    def __init__(self, session: AsyncSession, llm_client: LLMClient) -> None:
        self._session = session
        self._llm_client = llm_client

    async def extract_interests_from_prompt(self, prompt: str) -> InterestExtractionResult:
        """Extract interests from a natural language prompt using LLM.

        Returns:
            InterestExtractionResult with add_interests and remove_interests.

        Raises:
            InterestExtractionError: When the LLM layer fails (unavailable, auth, invalid response).
        """
        try:
            return await self._llm_client.extract_interests(prompt)
        except LLMServiceError as exc:
            raise InterestExtractionError(str(exc), exc.error_code) from exc
