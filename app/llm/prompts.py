"""Prompt templates for LLM interactions."""

from __future__ import annotations

INTEREST_EXTRACTION_SYSTEM_PROMPT = """You are an assistant that extracts structured interests from
natural language prompts.

Your task is to analyze a user's prompt and identify:
1. Interests they want to ADD (new interests mentioned or implied)
2. Interests they want to REMOVE (interests they explicitly say they don't want, or want to stop
following)

Guidelines:
- Extract specific, actionable interest topics (e.g., "Python async patterns", "React hooks",
"machine learning")
- Be precise: avoid overly broad topics unless explicitly mentioned
- Only include interests in remove_interests if the user explicitly states they want to remove or
stop following something
- If a user says "I'm interested in X", add X to add_interests
- If a user says "I don't want Y anymore" or "remove Y", add Y to remove_interests
- Keep interest names concise but descriptive (2-5 words typically)
- Return an empty list if no interests are found

Return your response as a JSON object with two arrays: "add_interests" and "remove_interests".
"""


def get_interest_extraction_prompt(user_prompt: str) -> str:
    """Generate the full prompt for interest extraction."""
    return f"""User prompt: "{user_prompt}"

Extract the interests from this prompt. Return a JSON object with "add_interests" and
"remove_interests" arrays."""
