from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion
from pydantic import ValidationError

from app.core.config import settings
from app.llm.prompts import (
    INTEREST_EXTRACTION_SYSTEM_PROMPT,
    get_interest_extraction_prompt,
)
from app.llm.schemas import InterestExtractionResult


class LLMServiceError(Exception):
    """Base error raised when the LLM service cannot fulfill a request."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class LLMUnavailableError(LLMServiceError):
    """LLM is unavailable (timeout, rate limit, or upstream outage)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "llm_unavailable")


class LLMAuthenticationError(LLMServiceError):
    """LLM authentication failed (service credentials invalid)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "llm_auth_failed")


class LLMInvalidResponseError(LLMServiceError):
    """LLM returned an invalid or unexpected response."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "llm_response_invalid")


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

    def _handle_errors(self, error: Exception) -> LLMServiceError:
        """Log error with appropriate message based on error type."""
        if isinstance(error, APIConnectionError):
            logging.error(f"OpenAI API connection failed. Error: {error}")
            return LLMUnavailableError("LLM service unreachable. Try again shortly.")
        elif isinstance(error, APITimeoutError):
            logging.error(f"OpenAI API request timed out. Error: {error}")
            return LLMUnavailableError("LLM request timed out. Try again.")
        elif isinstance(error, RateLimitError):
            logging.error(f"OpenAI API rate limit exceeded. Error: {error}")
            return LLMUnavailableError("LLM rate limit exceeded. Try again later.")
        elif isinstance(error, AuthenticationError):
            logging.error(f"OpenAI API authentication failed. Error: {error}")
            return LLMAuthenticationError("LLM authentication failed.")
        elif isinstance(error, APIError):
            logging.error(f"OpenAI API error. Error: {error}")
            return LLMUnavailableError("LLM service error. Try again later.")
        elif isinstance(error, (IndexError, AttributeError)):
            logging.error(f"Unexpected response structure from OpenAI. Error: {error}")
            return LLMInvalidResponseError("LLM returned an unexpected response.")
        elif isinstance(error, json.JSONDecodeError):
            logging.error(f"Invalid JSON response from OpenAI. Error: {error}")
            return LLMInvalidResponseError("LLM returned invalid JSON.")
        elif isinstance(error, ValidationError):
            logging.error(f"Pydantic validation failed. Error: {error}")
            return LLMInvalidResponseError("LLM response did not match expected format.")
        elif isinstance(error, ValueError):
            logging.error(f"Invalid value encountered. Error: {error}")
            return LLMInvalidResponseError(str(error))
        else:
            logging.error(f"Unexpected error extracting interests. Error: {error}")
            return LLMServiceError("LLM request failed. Try again later.", "llm_error")

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
            raise self._handle_errors(e) from e
