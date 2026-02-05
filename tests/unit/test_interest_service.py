"""Unit tests for interest extraction service.

These tests use a mocked LLM client to avoid real API calls and costs.
"""

from __future__ import annotations

import pytest

from app.llm.client import (
    LLMAuthenticationError,
    LLMClient,
    LLMInvalidResponseError,
    LLMUnavailableError,
)
from app.llm.schemas import InterestExtractionResult
from app.services.interest_service import (
    InterestExtractionError,
    extract_interests_from_prompt,
)


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self, result: InterestExtractionResult | None = None) -> None:
        """Initialize mock with optional predefined result."""
        self.result = result or InterestExtractionResult()
        self.last_prompt: str | None = None

    async def extract_interests(self, prompt: str) -> InterestExtractionResult:
        """Mock implementation that records the prompt and returns predefined result."""
        self.last_prompt = prompt
        return self.result


@pytest.mark.asyncio
async def test_extract_interests_success() -> None:
    """Test successful interest extraction."""
    # Arrange
    expected_result = InterestExtractionResult(
        add_interests=["Python", "FastAPI"], remove_interests=["JavaScript"]
    )
    mock_client = MockLLMClient(result=expected_result)
    prompt = "I'm interested in Python and FastAPI, but not JavaScript"

    # Act
    result = await extract_interests_from_prompt(prompt, mock_client)

    # Assert
    assert result == expected_result
    assert result.add_interests == ["Python", "FastAPI"]
    assert result.remove_interests == ["JavaScript"]
    assert mock_client.last_prompt == prompt


@pytest.mark.asyncio
async def test_extract_interests_empty_result() -> None:
    """Test interest extraction with empty result."""
    # Arrange
    expected_result = InterestExtractionResult()
    mock_client = MockLLMClient(result=expected_result)
    prompt = "No specific interests mentioned"

    # Act
    result = await extract_interests_from_prompt(prompt, mock_client)

    # Assert
    assert result == expected_result
    assert result.add_interests == []
    assert result.remove_interests == []
    assert mock_client.last_prompt == prompt


@pytest.mark.asyncio
async def test_extract_interests_only_adds() -> None:
    """Test interest extraction with only additions."""
    # Arrange
    expected_result = InterestExtractionResult(add_interests=["Machine Learning"])
    mock_client = MockLLMClient(result=expected_result)
    prompt = "I want to learn about machine learning"

    # Act
    result = await extract_interests_from_prompt(prompt, mock_client)

    # Assert
    assert result.add_interests == ["Machine Learning"]
    assert result.remove_interests == []
    assert mock_client.last_prompt == prompt


@pytest.mark.asyncio
async def test_extract_interests_only_removes() -> None:
    """Test interest extraction with only removals."""
    # Arrange
    expected_result = InterestExtractionResult(remove_interests=["JavaScript", "React"])
    mock_client = MockLLMClient(result=expected_result)
    prompt = "I'm no longer interested in JavaScript or React"

    # Act
    result = await extract_interests_from_prompt(prompt, mock_client)

    # Assert
    assert result.add_interests == []
    assert result.remove_interests == ["JavaScript", "React"]
    assert mock_client.last_prompt == prompt


class ErrorLLMClient(LLMClient):
    """Mock LLM client that raises a given error."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def extract_interests(self, prompt: str) -> InterestExtractionResult:
        raise self.error


@pytest.mark.asyncio
async def test_extract_interests_raises_interest_extraction_error_on_llm_unavailable() -> None:
    """Service translates LLMUnavailableError to InterestExtractionError."""
    # Arrange
    mock_client = ErrorLLMClient(LLMUnavailableError("Service unavailable"))

    # Act & Assert
    with pytest.raises(InterestExtractionError) as exc_info:
        await extract_interests_from_prompt("test prompt", mock_client)
    assert exc_info.value.error_code == "llm_unavailable"
    assert "unavailable" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_extract_interests_raises_interest_extraction_error_on_llm_auth_failed() -> None:
    """Service translates LLMAuthenticationError to InterestExtractionError."""
    # Arrange
    mock_client = ErrorLLMClient(LLMAuthenticationError("Auth failed"))

    # Act & Assert
    with pytest.raises(InterestExtractionError) as exc_info:
        await extract_interests_from_prompt("test prompt", mock_client)
    assert exc_info.value.error_code == "llm_auth_failed"


@pytest.mark.asyncio
async def test_extract_interests_raises_interest_extraction_error_on_llm_invalid_response() -> None:
    """Service translates LLMInvalidResponseError to InterestExtractionError."""
    # Arrange
    mock_client = ErrorLLMClient(LLMInvalidResponseError("Invalid JSON"))

    # Act & Assert
    with pytest.raises(InterestExtractionError) as exc_info:
        await extract_interests_from_prompt("test prompt", mock_client)
    assert exc_info.value.error_code == "llm_response_invalid"
