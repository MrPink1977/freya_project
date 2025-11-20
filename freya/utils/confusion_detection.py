"""Advanced confusion detection for LLM responses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfusionSignal:
    """A confusion signal with pattern and weight."""

    pattern: re.Pattern
    weight: float  # 0.0 - 1.0
    category: str  # "uncertainty", "lack_of_knowledge", "apology"


# High-confidence confusion patterns (word boundaries enforced)
HIGH_CONFIDENCE_PATTERNS = [
    ConfusionSignal(
        pattern=re.compile(r"\b(i|i'm)\s+(really\s+)?(not|don't|dont)\s+sure\b", re.IGNORECASE),
        weight=0.9,
        category="uncertainty",
    ),
    ConfusionSignal(
        pattern=re.compile(
            r"\bi\s+don'?t\s+(really\s+)?know\s+(how|what|why|if|whether)\b", re.IGNORECASE
        ),
        weight=0.85,
        category="lack_of_knowledge",
    ),
    ConfusionSignal(
        pattern=re.compile(
            r"\bi\s+(don'?t\s+have|lack|dont\s+have)\s+(information|data|knowledge|details|the\s+\w+)\b",
            re.IGNORECASE,
        ),
        weight=0.95,
        category="lack_of_knowledge",
    ),
    ConfusionSignal(
        pattern=re.compile(
            r"\bi'?m\s+(unable|not\s+able)\s+to\s+(help|assist|answer|provide)\b",
            re.IGNORECASE,
        ),
        weight=0.9,
        category="lack_of_knowledge",
    ),
]

# Medium-confidence patterns (context-dependent)
MEDIUM_CONFIDENCE_PATTERNS = [
    ConfusionSignal(
        pattern=re.compile(r"\bi\s+apologize,?\s+but\s+i\b", re.IGNORECASE),
        weight=0.7,
        category="apology",
    ),
    ConfusionSignal(
        pattern=re.compile(r"\bsorry,?\s+(but\s+)?i\s+(don'?t|can'?t|dont|cant|cannot)\b", re.IGNORECASE),
        weight=0.75,
        category="apology",
    ),
    ConfusionSignal(
        pattern=re.compile(r"\b(unclear|uncertain|unsure|ambiguous)\b", re.IGNORECASE),
        weight=0.70,
        category="uncertainty",
    ),
    ConfusionSignal(
        pattern=re.compile(r"\bi\s+might\s+be\s+(wrong|mistaken|incorrect)\b", re.IGNORECASE),
        weight=0.70,
        category="uncertainty",
    ),
]

# Low-confidence patterns (need multiple occurrences)
LOW_CONFIDENCE_PATTERNS = [
    ConfusionSignal(
        pattern=re.compile(r"\b(perhaps|maybe|possibly|potentially)\b", re.IGNORECASE),
        weight=0.3,
        category="uncertainty",
    ),
    ConfusionSignal(
        pattern=re.compile(r"\bi\s+(think|believe|assume)\b", re.IGNORECASE),
        weight=0.25,
        category="uncertainty",
    ),
]

# False positive filters (these indicate the response is actually helpful)
FALSE_POSITIVE_FILTERS = [
    re.compile(r"\bi\s+don'?t\s+know\s+(about|of)\s+\w+,?\s+but\s+(here|i\s+can)\b", re.IGNORECASE),
    re.compile(r"\bwhile\s+i\s+don'?t\b", re.IGNORECASE),
    re.compile(r"\balthough\s+i\s+don'?t\b", re.IGNORECASE),
    re.compile(r"\beven\s+though\s+i\s+don'?t\b", re.IGNORECASE),
]


def detect_confusion(
    response: str,
    *,
    threshold: float = 0.7,
    require_early_occurrence: bool = True,
) -> tuple[bool, float, Optional[str]]:
    """
    Detect confusion in LLM response with confidence scoring.

    Args:
        response: LLM response text
        threshold: Confidence threshold for confusion (0.0-1.0)
        require_early_occurrence: Require confusion signals in first 150 chars

    Returns:
        Tuple of (is_confused, confidence_score, detected_category)
    """
    if not response or not response.strip():
        return False, 0.0, None

    # Check false positive filters first
    for filter_pattern in FALSE_POSITIVE_FILTERS:
        if filter_pattern.search(response):
            return False, 0.0, None

    # Focus on first 150 characters if early occurrence required
    search_text = response[:150] if require_early_occurrence else response

    max_score = 0.0
    detected_category = None

    # Check high-confidence patterns
    for signal in HIGH_CONFIDENCE_PATTERNS:
        if signal.pattern.search(search_text):
            if signal.weight > max_score:
                max_score = signal.weight
                detected_category = signal.category

    # Check medium-confidence patterns
    for signal in MEDIUM_CONFIDENCE_PATTERNS:
        if signal.pattern.search(search_text):
            if signal.weight > max_score:
                max_score = signal.weight
                detected_category = signal.category

    # Check low-confidence patterns (need multiple)
    low_conf_score = 0.0
    for signal in LOW_CONFIDENCE_PATTERNS:
        matches = signal.pattern.findall(response)  # Count all matches
        if matches:
            low_conf_score += len(matches) * signal.weight

    # Multiple low-confidence signals can accumulate
    if low_conf_score > max_score:
        max_score = low_conf_score
        detected_category = "uncertainty"

    is_confused = max_score >= threshold
    return is_confused, max_score, detected_category


__all__ = ["detect_confusion", "ConfusionSignal"]
