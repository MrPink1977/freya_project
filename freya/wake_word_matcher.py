# freya/wake_word_matcher.py

import re
from difflib import SequenceMatcher


class WakeWordMatcher:
    """Fuzzy wake word matcher with token-based detection."""
    
    def __init__(
        self,
        wake_word: str = "Hey, Freya",
        sensitivity: float = 0.75,
        token_offset_limit: int = 2,
    ):
        """
        Initialize wake word matcher.
        
        Args:
            wake_word: Wake word phrase to detect
            sensitivity: Match sensitivity (0-1, higher = stricter)
            token_offset_limit: Max tokens allowed before/after wake word
        """
        self.wake_word = wake_word.lower()
        self.wake_word_display = wake_word
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        self.token_offset_limit = token_offset_limit
        
        # Tokenize wake word
        self.wake_tokens = self._tokenize(self.wake_word)
    
    def _tokenize(self, text: str) -> list[str]:
        """Split text into tokens."""
        return re.findall(r'\w+', text.lower())
    
    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match ratio between two strings."""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def find_wake_word(self, transcript: str) -> tuple[bool, str]:
        """
        Find wake word in transcript using fuzzy matching.
        
        Args:
            transcript: Input transcript to search
            
        Returns:
            (detected, remainder): Whether wake word detected and remaining text
        """
        if not transcript:
            return False, ""
        
        transcript_lower = transcript.lower()
        tokens = self._tokenize(transcript_lower)
        
        if not tokens:
            return False, ""
        
        # Try to find wake word sequence
        wake_len = len(self.wake_tokens)
        
        for i in range(len(tokens) - wake_len + 1):
            # Check if this position might be wake word
            window = tokens[i:i + wake_len]
            
            # Calculate match score
            match_score = sum(
                self._fuzzy_match(wake_tok, trans_tok)
                for wake_tok, trans_tok in zip(self.wake_tokens, window)
            ) / wake_len
            
            if match_score >= self.sensitivity:
                # Found wake word! Extract remainder
                remainder_tokens = tokens[i + wake_len:]
                remainder = " ".join(remainder_tokens)
                return True, remainder
        
        return False, ""
