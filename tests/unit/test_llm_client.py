"""Unit tests for LLM client implementation.

These tests mock the OpenAI SDK to avoid real API calls and costs.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from pydantic import ValidationError

from app.llm.client import OpenAIClient
from app.llm.schemas import InterestExtractionResult


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    """Create a mock OpenAI client."""
    return AsyncMock()


@pytest.fixture
def llm_client(mock_openai_client: AsyncMock) -> OpenAIClient:
    """Create LLM client with mocked OpenAI client."""
    client = OpenAIClient()
    client.client = mock_openai_client
    return client


def _create_chat_completion(content: str) -> ChatCompletion:
    """Helper to create a ChatCompletion object."""
    return ChatCompletion(
        id="test-id",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content=content, role="assistant", function_call=None, tool_calls=None
                ),
            )
        ],
        created=1234567890,
        model="gpt-4o-mini",
        object="chat.completion",
    )


@pytest.mark.asyncio
async def test_extract_interests_success(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test successful interest extraction."""
    # Arrange
    response_data = {"add_interests": ["Python", "FastAPI"], "remove_interests": ["JavaScript"]}
    mock_response = _create_chat_completion(json.dumps(response_data))
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Act
    result = await llm_client.extract_interests("I like Python and FastAPI, not JavaScript")

    # Assert
    assert isinstance(result, InterestExtractionResult)
    assert result.add_interests == ["Python", "FastAPI"]
    assert result.remove_interests == ["JavaScript"]
    mock_openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_extract_interests_empty_result(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test interest extraction with empty result."""
    # Arrange
    response_data = {"add_interests": [], "remove_interests": []}
    mock_response = _create_chat_completion(json.dumps(response_data))
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Act
    result = await llm_client.extract_interests("No specific interests")

    # Assert
    assert result.add_interests == []
    assert result.remove_interests == []


@pytest.mark.asyncio
async def test_extract_interests_empty_response(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of empty response from OpenAI."""
    # Arrange
    mock_response = _create_chat_completion("")
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Act & Assert - client logs error and re-raises
    with pytest.raises(ValueError, match="Empty response from OpenAI"):
        await llm_client.extract_interests("test prompt")


@pytest.mark.asyncio
async def test_extract_interests_invalid_json(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of invalid JSON response."""
    # Arrange
    mock_response = _create_chat_completion("not valid json")
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Act & Assert - client logs error and re-raises
    with pytest.raises(json.JSONDecodeError):
        await llm_client.extract_interests("test prompt")


@pytest.mark.asyncio
async def test_extract_interests_validation_error(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of Pydantic validation error."""
    # Arrange
    response_data = {"add_interests": "not a list"}  # Invalid: should be list
    mock_response = _create_chat_completion(json.dumps(response_data))
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Act & Assert - client logs error and re-raises
    with pytest.raises(ValidationError):
        await llm_client.extract_interests("test prompt")


@pytest.mark.asyncio
async def test_extract_interests_api_connection_error(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of API connection error."""
    # Arrange
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=None)
    )

    # Act & Assert - client logs error and re-raises
    with pytest.raises(APIConnectionError):
        await llm_client.extract_interests("test prompt")


@pytest.mark.asyncio
async def test_extract_interests_api_timeout_error(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of API timeout error."""
    # Arrange
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=APITimeoutError(request=None)
    )

    # Act & Assert - client logs error and re-raises
    with pytest.raises(APITimeoutError):
        await llm_client.extract_interests("test prompt")


@pytest.mark.asyncio
async def test_extract_interests_rate_limit_error(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of rate limit error."""
    # Arrange - RateLimitError requires response and body
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=RateLimitError(message="Rate limited", response=mock_response, body={})
    )

    # Act & Assert - client logs error and re-raises
    with pytest.raises(RateLimitError):
        await llm_client.extract_interests("test prompt")


@pytest.mark.asyncio
async def test_extract_interests_authentication_error(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of authentication error."""
    # Arrange - AuthenticationError requires response and body
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=AuthenticationError(message="Auth failed", response=mock_response, body={})
    )

    # Act & Assert - client logs error and re-raises
    with pytest.raises(AuthenticationError):
        await llm_client.extract_interests("test prompt")


@pytest.mark.asyncio
async def test_extract_interests_unexpected_structure(
    llm_client: OpenAIClient, mock_openai_client: AsyncMock
) -> None:
    """Test handling of unexpected response structure."""
    # Arrange - simulate missing choices[0]
    mock_response = MagicMock(spec=ChatCompletion)
    mock_response.choices = []
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Act & Assert - client logs error and re-raises
    with pytest.raises((IndexError, AttributeError)):
        await llm_client.extract_interests("test prompt")
