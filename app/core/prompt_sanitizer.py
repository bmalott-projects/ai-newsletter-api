from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_CODE_BLOCK_PATTERN = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")
_URL_PATTERN = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_INJECTION_PATTERNS = [
    re.compile(r"ignore (all|previous|prior) instructions", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"developer message", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]


class PromptValidationError(ValueError):
    """Raised when prompt sanitization fails."""

    error_code: str = "invalid_prompt"


def sanitize_prompt(prompt: str) -> str:
    """Sanitize prompt input and return safe text for LLM usage."""
    if _CONTROL_CHARS_PATTERN.search(prompt):
        raise PromptValidationError("Prompt contains unsupported control characters.")
    if _URL_PATTERN.search(prompt):
        raise PromptValidationError("Prompt must not include URLs.")
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(prompt):
            raise PromptValidationError("Prompt contains disallowed instruction patterns.")

    sanitized = _CODE_BLOCK_PATTERN.sub(" ", prompt)
    sanitized = _INLINE_CODE_PATTERN.sub(" ", sanitized)
    sanitized = " ".join(sanitized.split())

    if not sanitized:
        raise PromptValidationError("Prompt must include valid text after sanitization.")

    if sanitized != prompt:
        logger.info(
            "Sanitized prompt input",
            extra={"original_length": len(prompt), "sanitized_length": len(sanitized)},
        )

    return sanitized
