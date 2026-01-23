"""Unit tests for interest extraction service.

These tests use a mocked LLM client to avoid real API calls and costs.
"""

from __future__ import annotations

import pytest

from app.llm.client import LLMClient
from app.llm.schemas import InterestExtractionResult
from app.services.interest import extract_interests_from_prompt


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
