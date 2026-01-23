from __future__ import annotations

from app.llm.client import LLMClient
from app.llm.schemas import InterestExtractionResult


async def extract_interests_from_prompt(
    prompt: str, llm_client: LLMClient
) -> InterestExtractionResult:
    """Extract interests from a natural language prompt using LLM."""
    return await llm_client.extract_interests(prompt)
