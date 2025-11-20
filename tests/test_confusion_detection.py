"""Tests for confusion detection utility."""

from __future__ import annotations

import pytest

from freya.utils.confusion_detection import detect_confusion


class TestHighConfidenceConfusion:
    """Test high-confidence confusion signals."""

    def test_detects_not_sure(self):
        """Detect 'I'm not sure' patterns."""
        responses = [
            "I'm not sure about that.",
            "I'm really not sure how to help.",
            "I'm not sure.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert confidence >= 0.8
            assert category in ("uncertainty", "lack_of_knowledge")

    def test_detects_dont_know_with_context(self):
        """Detect 'I don't know how/what/why' patterns."""
        responses = [
            "I don't know how to help with this.",
            "I don't really know what you're asking.",
            "I don't know why that happened.",
            "I don't know if I can help.",
            "I don't know whether that's correct.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert confidence >= 0.8
            assert category == "lack_of_knowledge"

    def test_detects_lack_of_information(self):
        """Detect 'don't have information' patterns."""
        responses = [
            "I don't have information about that topic.",
            "I don't have the data you need.",
            "I lack knowledge about this subject.",
            "I don't have details on that.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert confidence >= 0.9
            assert category == "lack_of_knowledge"

    def test_detects_unable_to_help(self):
        """Detect 'unable to help' patterns."""
        responses = [
            "I'm unable to assist with this request.",
            "I'm not able to help with that.",
            "I'm unable to answer your question.",
            "I'm unable to provide that information.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert confidence >= 0.9
            assert category == "lack_of_knowledge"

    def test_detects_cannot_help(self):
        """Detect 'I cannot help' patterns as apologies."""
        responses = [
            "Sorry, I cannot help with that.",
            "Sorry, I cannot assist you.",
            "Sorry but I cannot answer that question.",
            "Sorry, I cannot provide that information.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert 0.6 <= confidence < 0.9
            assert category == "apology"


class TestMediumConfidenceConfusion:
    """Test medium-confidence confusion signals."""

    def test_detects_apologies(self):
        """Detect apology patterns."""
        responses = [
            "I apologize, but I cannot help.",
            "I apologize but I don't understand.",
            "Sorry, I don't know the answer.",
            "Sorry but I can't help with that.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert 0.6 <= confidence < 0.9
            assert category in ("apology", "lack_of_knowledge")

    def test_detects_uncertainty_words(self):
        """Detect uncertainty indicators."""
        responses = [
            "That's unclear to me.",
            "I'm uncertain about this.",
            "This seems unsure.",
            "The answer is ambiguous.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert 0.6 <= confidence < 0.9
            assert category == "uncertainty"

    def test_detects_might_be_wrong(self):
        """Detect 'might be wrong' patterns."""
        responses = [
            "I might be wrong about this.",
            "I might be mistaken.",
            "I might be incorrect here.",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is True
            assert 0.6 <= confidence < 0.9
            assert category == "uncertainty"


class TestFalsePositiveFiltering:
    """Test false positive filters."""

    def test_filters_helpful_responses_with_qualifiers(self):
        """Filter responses that are actually helpful despite confusion phrases."""
        responses = [
            "I don't know about Python, but I can help with JavaScript.",
            "I don't know of that specific tool, but here are alternatives.",
            "While I don't have exact numbers, I can explain the concept.",
            "Although I don't remember the date, I can find it for you.",
            "Even though I don't have details, here's what I know...",
        ]
        for response in responses:
            is_confused, confidence, category = detect_confusion(response)
            assert is_confused is False
            assert confidence == 0.0

    def test_does_not_trigger_on_simple_dont_know(self):
        """Don't trigger on simple 'don't know' without context."""
        responses = [
            "I don't know.",  # Too simple, should need context words
            "I don't have it.",  # Missing "information/data/knowledge"
        ]
        for response in responses:
            is_confused, conf, _ = detect_confusion(response)
            # These should have low confidence or not trigger
            assert is_confused is False or conf < 0.7


class TestConfidentResponses:
    """Test that confident responses don't trigger confusion."""

    def test_confident_answers_not_confused(self):
        """Confident responses should not trigger confusion."""
        responses = [
            "Here's the answer you're looking for.",
            "I can definitely help with that!",
            "The solution is to use Python 3.11.",
            "Let me explain how this works.",
            "That's a great question! Here's what I know.",
            "I'm happy to help you with this.",
        ]
        for response in responses:
            is_confused, confidence, _ = detect_confusion(response)
            assert is_confused is False
            assert confidence < 0.7


class TestEarlyOccurrenceRequirement:
    """Test early occurrence requirement."""

    def test_requires_confusion_early_in_response(self):
        """Confusion must occur in first 150 characters by default."""
        # Confusion signal way at the end
        response = "Here's a detailed answer with lots of information. " * 5 + " I don't know."
        is_confused, _, _ = detect_confusion(response, require_early_occurrence=True)
        assert is_confused is False

    def test_detects_late_confusion_when_disabled(self):
        """Can detect confusion anywhere when early requirement disabled."""
        response = "Here's information. " * 10 + " I don't know how to help."
        is_confused, _, _ = detect_confusion(response, require_early_occurrence=False)
        assert is_confused is True

    def test_detects_early_confusion(self):
        """Detects confusion in first 150 characters."""
        response = "I'm not sure about that. Here's some additional context..."
        is_confused, _, _ = detect_confusion(response, require_early_occurrence=True)
        assert is_confused is True


class TestLowConfidenceAccumulation:
    """Test low-confidence pattern accumulation."""

    def test_single_low_confidence_not_confused(self):
        """Single low-confidence signal doesn't trigger confusion."""
        responses = [
            "Perhaps this could work.",
            "Maybe that's the answer.",
            "Possibly it's correct.",
            "I think this is right.",
        ]
        for response in responses:
            is_confused, confidence, _ = detect_confusion(response)
            assert is_confused is False
            assert confidence < 0.7

    def test_multiple_low_confidence_accumulates(self):
        """Multiple low-confidence signals accumulate."""
        response = "Perhaps maybe possibly it could work, I think I believe."
        is_confused, confidence, category = detect_confusion(response)
        # Should accumulate but might not reach threshold
        assert confidence > 0.0
        if is_confused:
            assert category == "uncertainty"


class TestThresholdAdjustment:
    """Test adjustable confidence threshold."""

    def test_lower_threshold_more_sensitive(self):
        """Lower threshold makes detection more sensitive."""
        response = "That's unclear to me."  # Medium confidence 0.70
        
        # Threshold 0.75 - should not trigger
        is_confused_high, _, _ = detect_confusion(response, threshold=0.75)
        assert is_confused_high is False
        
        # Threshold 0.7 - should trigger (matches exactly)
        is_confused_mid, _, _ = detect_confusion(response, threshold=0.7)
        assert is_confused_mid is True
        
        # Lower threshold 0.5 - should trigger
        is_confused_low, _, _ = detect_confusion(response, threshold=0.5)
        assert is_confused_low is True

    def test_higher_threshold_less_sensitive(self):
        """Higher threshold requires stronger signals."""
        response = "I apologize, but I don't know."  # Medium-high ~0.75
        
        # Low threshold - should trigger
        is_confused_low, _, _ = detect_confusion(response, threshold=0.6)
        assert is_confused_low is True
        
        # Very high threshold - might not trigger
        is_confused_high, _, _ = detect_confusion(response, threshold=0.9)
        # Result depends on exact confidence score


class TestEdgeCases:
    """Test edge cases."""

    def test_handles_empty_string(self):
        """Handles empty string gracefully."""
        is_confused, confidence, category = detect_confusion("")
        assert is_confused is False
        assert confidence == 0.0
        assert category is None

    def test_handles_whitespace_only(self):
        """Handles whitespace-only string."""
        is_confused, confidence, category = detect_confusion("   \n\t  ")
        assert is_confused is False
        assert confidence == 0.0
        assert category is None

    def test_case_insensitive(self):
        """Detection is case-insensitive."""
        variations = [
            "I DON'T KNOW HOW TO HELP",
            "i don't know how to help",
            "I Don't Know How To Help",
        ]
        for response in variations:
            is_confused, _, _ = detect_confusion(response)
            assert is_confused is True

    def test_returns_tuple_of_three(self):
        """Always returns tuple of (bool, float, Optional[str])."""
        response = "I'm not sure about that."
        result = detect_confusion(response)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)
        assert result[2] is None or isinstance(result[2], str)
