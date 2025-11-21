"""Tests for shared fact patterns utility."""

from __future__ import annotations

from freya.utils.fact_patterns import (
    EXTRACTION_PATTERNS,
    FACT_QUERY_PHRASES,
    QUESTION_INDICATORS,
    get_extraction_patterns,
    get_query_phrases,
    is_question,
)


class TestExtractionPatterns:
    """Test extraction pattern access."""

    def test_get_extraction_patterns_returns_dict(self):
        """Returns dictionary of regex patterns."""
        patterns = get_extraction_patterns()
        assert isinstance(patterns, dict)
        assert len(patterns) == 9

    def test_pattern_names_present(self):
        """All expected patterns are present."""
        patterns = get_extraction_patterns()
        expected = [
            "name_is",
            "call_me",
            "birthday_is",
            "born_on",
            "favorite",
            "i_like",
            "i_love",
            "i_hate",
            "i_dislike",
        ]
        for pattern_name in expected:
            assert pattern_name in patterns

    def test_patterns_are_compiled(self):
        """Patterns are compiled regex objects."""
        import re

        patterns = get_extraction_patterns()
        for pattern in patterns.values():
            assert isinstance(pattern, re.Pattern)

    def test_name_pattern_matches(self):
        """Name pattern matches expected strings."""
        patterns = get_extraction_patterns()

        assert patterns["name_is"].search("My name is Alice")
        assert patterns["name_is"].search("my name's Bob")
        assert patterns["call_me"].search("Call me Charlie")
        assert patterns["call_me"].search("You can call me Dave")


class TestQueryPhrases:
    """Test query phrase access."""

    def test_get_query_phrases_for_name(self):
        """Returns name query phrases."""
        phrases = get_query_phrases("name")
        assert isinstance(phrases, list)
        assert "my name" in phrases
        assert "who am i" in phrases
        assert len(phrases) == 4

    def test_get_query_phrases_for_birthday(self):
        """Returns birthday query phrases."""
        phrases = get_query_phrases("birthday")
        assert isinstance(phrases, list)
        assert "my birthday" in phrases
        assert "when was i born" in phrases

    def test_get_query_phrases_for_likes(self):
        """Returns likes query phrases."""
        phrases = get_query_phrases("likes")
        assert isinstance(phrases, list)
        assert "what do i like" in phrases
        assert "my favorite" in phrases

    def test_get_query_phrases_for_dislikes(self):
        """Returns dislikes query phrases."""
        phrases = get_query_phrases("dislikes")
        assert isinstance(phrases, list)
        assert "what do i dislike" in phrases
        assert "things i hate" in phrases

    def test_get_query_phrases_unknown_category(self):
        """Returns empty list for unknown category."""
        phrases = get_query_phrases("unknown_category")
        assert phrases == []


class TestQuestionDetection:
    """Test question detection logic."""

    def test_detects_questions_starting_with_indicators(self):
        """Detects questions starting with question words."""
        questions = [
            "What is your name?",
            "When were you born?",
            "Where do you live?",
            "Who is your friend?",
            "Why do you think that?",
            "How does this work?",
            "Can you help me?",
            "Do you know my birthday?",
            "Will you remember this?",
            "Should I tell you more?",
        ]
        for question in questions:
            assert is_question(question) is True

    def test_detects_questions_with_mid_sentence_indicators(self):
        """Detects questions with indicators mid-sentence."""
        questions = [
            "Tell me, do you know?",
            "I wonder what time it is",
            "Please tell me when this happened",
        ]
        for question in questions:
            assert is_question(question) is True

    def test_does_not_detect_statements(self):
        """Does not detect statements as questions."""
        statements = [
            "My name is Alice.",
            "I was born in 1990.",
            "I really like programming.",
            "This is interesting.",
            "Programming is fun.",
        ]
        for statement in statements:
            assert is_question(statement) is False

    def test_case_insensitive(self):
        """Question detection is case-insensitive."""
        assert is_question("WHAT IS YOUR NAME?") is True
        assert is_question("what is your name?") is True
        assert is_question("What Is Your Name?") is True

    def test_handles_empty_string(self):
        """Handles empty string gracefully."""
        assert is_question("") is False
        assert is_question("   ") is False


class TestModuleExports:
    """Test module exports."""

    def test_exports_constants(self):
        """Module exports expected constants."""
        assert EXTRACTION_PATTERNS is not None
        assert FACT_QUERY_PHRASES is not None
        assert QUESTION_INDICATORS is not None

    def test_constants_are_correct_type(self):
        """Constants have correct types."""
        assert isinstance(EXTRACTION_PATTERNS, dict)
        assert isinstance(FACT_QUERY_PHRASES, dict)
        assert isinstance(QUESTION_INDICATORS, list)
