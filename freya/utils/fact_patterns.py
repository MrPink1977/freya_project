"""Shared fact extraction and retrieval patterns for Freya."""

from __future__ import annotations

import re
from typing import Dict, List

# Extraction patterns for user statements
EXTRACTION_PATTERNS = {
    "name_is": re.compile(r"my name(?:'s| is) (\w+(?:\s+\w+)?)", re.IGNORECASE),
    "call_me": re.compile(r"(?:you can |just )?call me (\w+)", re.IGNORECASE),
    "birthday_is": re.compile(
        r"my birthday(?:'s| is) ([a-z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?)",
        re.IGNORECASE,
    ),
    "born_on": re.compile(
        r"(?:i was )?born (?:on |in )?([a-z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?|\d{4}|[a-z]+ \d{4})",
        re.IGNORECASE,
    ),
    "favorite": re.compile(r"my favorite (\w+) is ([^.,!?]+)", re.IGNORECASE),
    "i_like": re.compile(r"i (?:really |absolutely )?like ([^.,!?]+)", re.IGNORECASE),
    "i_love": re.compile(r"i (?:really |absolutely )?love ([^.,!?]+)", re.IGNORECASE),
    "i_hate": re.compile(r"i (?:really |absolutely )?hate ([^.,!?]+)", re.IGNORECASE),
    "i_dislike": re.compile(r"i (?:really |absolutely )?dislike ([^.,!?]+)", re.IGNORECASE),
}

# Query phrases for fact retrieval
FACT_QUERY_PHRASES = {
    "name": ["my name", "what's my name", "who am i", "do you know my name"],
    "birthday": ["my birthday", "when was i born", "when am i born", "my birth"],
    "likes": ["what do i like", "things i like", "my favorite", "do i like"],
    "dislikes": ["what do i dislike", "what don't i like", "things i hate", "do i dislike"],
}

# Question indicators to skip during extraction
QUESTION_INDICATORS = [
    "do you",
    "can you",
    "what",
    "when",
    "where",
    "who",
    "why",
    "how",
    "is it",
    "are you",
    "will you",
    "should",
    "could",
    "would",
    "remember my",
    "know my",
    "recall",
]


def is_question(text: str) -> bool:
    """
    Check if text is a question rather than a statement.

    Args:
        text: Text to check

    Returns:
        True if text appears to be a question
    """
    lowered = text.lower().strip()
    return any(
        lowered.startswith(indicator) or f" {indicator}" in lowered
        for indicator in QUESTION_INDICATORS
    )


def get_extraction_patterns() -> Dict[str, re.Pattern]:
    """
    Get all fact extraction patterns.

    Returns:
        Dictionary of pattern name to compiled regex
    """
    return EXTRACTION_PATTERNS.copy()


def get_query_phrases(category: str) -> List[str]:
    """
    Get query phrases for a fact category.

    Args:
        category: Fact category (name, birthday, likes, dislikes)

    Returns:
        List of query phrases for the category
    """
    return FACT_QUERY_PHRASES.get(category, [])


__all__ = [
    "EXTRACTION_PATTERNS",
    "FACT_QUERY_PHRASES",
    "QUESTION_INDICATORS",
    "is_question",
    "get_extraction_patterns",
    "get_query_phrases",
]
