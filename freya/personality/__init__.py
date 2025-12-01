"""
Simplified Personality System for Freya.

Provides emotion detection, intent classification, and adaptive personality
without complex async agent architecture.
"""

from freya.personality.analyzer import ContextAnalyzer
from freya.personality.engine import PersonalityEngine
from freya.personality.traits import EmotionalState, PersonalityMode, PersonalityTraits

__all__ = [
    "PersonalityEngine",
    "ContextAnalyzer",
    "PersonalityTraits",
    "EmotionalState",
    "PersonalityMode",
]
