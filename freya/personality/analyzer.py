"""
Context Analyzer - Emotion and intent detection (synchronous).

Analyzes user queries to detect emotions, intents, and context.
"""

import re
from dataclasses import dataclass
from enum import Enum


class UserEmotion(Enum):
    """Detected user emotions."""
    HAPPY = "happy"
    EXCITED = "excited"
    NEUTRAL = "neutral"
    CURIOUS = "curious"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    SAD = "sad"
    ANXIOUS = "anxious"
    PLAYFUL = "playful"


class UserIntent(Enum):
    """Detected user intents."""
    # Information seeking
    ASK_QUESTION = "ask_question"
    ASK_HELP = "ask_help"
    ASK_OPINION = "ask_opinion"

    # Emotional/Social
    SHARE_GOOD_NEWS = "share_good_news"
    SHARE_BAD_NEWS = "share_bad_news"
    VENT = "vent"
    CELEBRATE = "celebrate"
    JOKE = "joke"

    # Task-oriented
    REQUEST_ACTION = "request_action"
    TROUBLESHOOT = "troubleshoot"

    # Conversational
    SMALL_TALK = "small_talk"
    PHILOSOPHICAL = "philosophical"
    GREETING = "greeting"
    GOODBYE = "goodbye"

    UNKNOWN = "unknown"


@dataclass
class ContextAnalysis:
    """Complete analysis of user query."""
    emotion: UserEmotion
    intent: UserIntent
    urgency: float  # 0-1 scale
    sentiment: float  # -1 to 1
    conversation_type: str  # "task", "social", "deep", "casual"


class ContextAnalyzer:
    """Analyzes user queries for emotion, intent, and context."""

    def __init__(self):
        """Initialize context analyzer with pattern matchers."""
        self._emotion_keywords = {
            UserEmotion.HAPPY: ["happy", "glad", "pleased", "good", "great", "awesome", "nice", "love it", "perfect"],
            UserEmotion.EXCITED: ["excited", "can't wait", "omg", "amazing", "incredible", "wow", "!!!!", "yes!!"],
            UserEmotion.FRUSTRATED: ["frustrated", "annoying", "annoyed", "ugh", "argh", "seriously", "not working"],
            UserEmotion.ANGRY: ["angry", "pissed", "furious", "mad", "hate", "ridiculous"],
            UserEmotion.SAD: ["sad", "depressed", "down", "unhappy", "miserable", "devastated", "terrible", "awful"],
            UserEmotion.ANXIOUS: ["anxious", "worried", "nervous", "stressed", "scared", "concerned", "overwhelmed"],
            UserEmotion.CONFUSED: ["confused", "lost", "don't understand", "makes no sense", "unclear", "huh"],
            UserEmotion.PLAYFUL: ["haha", "lol", "kidding", "joking", "funny", "playful"],
            UserEmotion.CURIOUS: ["curious", "wondering", "interested", "fascinating", "how come", "why", "interesting"],
        }

        self._intent_patterns = {
            UserIntent.ASK_QUESTION: [
                re.compile(r"\b(what|when|where|who|which)\b", re.IGNORECASE),
                re.compile(r"\bhow (do|does|did|can|could|would|should)\b", re.IGNORECASE),
                re.compile(r"\?$"),
            ],
            UserIntent.ASK_HELP: [
                re.compile(r"\b(help|assist|stuck|don't know how)\b", re.IGNORECASE),
                re.compile(r"\b(can you|could you) (help|show|teach)\b", re.IGNORECASE),
            ],
            UserIntent.SHARE_GOOD_NEWS: [
                re.compile(r"\b(i got|i passed|i won|i made|i finished)\b", re.IGNORECASE),
                re.compile(r"\b(guess what|great news)\b", re.IGNORECASE),
            ],
            UserIntent.SHARE_BAD_NEWS: [
                re.compile(r"\b(i failed|i lost|i didn't|i missed|i broke)\b", re.IGNORECASE),
                re.compile(r"\b(bad news|terrible|awful|worst)\b", re.IGNORECASE),
            ],
            UserIntent.VENT: [
                re.compile(r"\b(so annoyed|so frustrated|can't believe)\b", re.IGNORECASE),
                re.compile(r"\b(hate|sick of|tired of|fed up|done with)\b", re.IGNORECASE),
            ],
            UserIntent.JOKE: [
                re.compile(r"\b(haha|lol|joke|funny|kidding)\b", re.IGNORECASE),
            ],
            UserIntent.PHILOSOPHICAL: [
                re.compile(r"\b(why do|what's the point|meaning of|purpose of)\b", re.IGNORECASE),
            ],
            UserIntent.GREETING: [
                re.compile(r"^(hey|hi|hello|yo|sup)\b", re.IGNORECASE),
            ],
            UserIntent.GOODBYE: [
                re.compile(r"\b(bye|goodbye|see ya|later|gotta go)\b", re.IGNORECASE),
            ],
        }

        self._urgency_signals = ["urgent", "asap", "quickly", "right now", "immediately", "help!", "need", "must"]

    def analyze(self, query: str) -> ContextAnalysis:
        """
        Analyze user query for emotion, intent, and context.

        Args:
            query: User's query text

        Returns:
            ContextAnalysis with detected emotion, intent, urgency, etc.
        """
        emotion = self._detect_emotion(query)
        intent = self._detect_intent(query)
        urgency = self._calculate_urgency(query)
        sentiment = self._calculate_sentiment(emotion)
        conversation_type = self._classify_conversation_type(intent)

        return ContextAnalysis(
            emotion=emotion,
            intent=intent,
            urgency=urgency,
            sentiment=sentiment,
            conversation_type=conversation_type,
        )

    def _detect_emotion(self, query: str) -> UserEmotion:
        """Detect user emotion from query text."""
        query_lower = query.lower()

        # Score each emotion
        emotion_scores = {}
        for emotion, keywords in self._emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                emotion_scores[emotion] = score

        # Boost excited/angry for high intensity (exclamations, caps)
        exclamation_count = query.count("!")
        caps_ratio = sum(1 for c in query if c.isupper()) / max(1, len(query))

        if exclamation_count >= 2 or caps_ratio > 0.3:
            if emotion_scores.get(UserEmotion.HAPPY, 0) > 0:
                emotion_scores[UserEmotion.EXCITED] = emotion_scores.get(UserEmotion.EXCITED, 0) + 2
            elif emotion_scores.get(UserEmotion.FRUSTRATED, 0) > 0:
                emotion_scores[UserEmotion.ANGRY] = emotion_scores.get(UserEmotion.ANGRY, 0) + 2

        # Return highest scoring emotion
        if emotion_scores:
            return max(emotion_scores.items(), key=lambda x: x[1])[0]

        return UserEmotion.NEUTRAL

    def _detect_intent(self, query: str) -> UserIntent:
        """Detect user intent from query text."""
        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    return intent

        return UserIntent.UNKNOWN

    def _calculate_urgency(self, query: str) -> float:
        """Calculate urgency score (0-1)."""
        query_lower = query.lower()

        urgency_score = 0.3  # Base urgency

        # Check for urgency signals
        for signal in self._urgency_signals:
            if signal in query_lower:
                urgency_score += 0.2

        # Exclamation marks indicate urgency
        exclamation_count = query.count("!")
        urgency_score += min(0.3, exclamation_count * 0.1)

        # Questions are moderately urgent
        if "?" in query:
            urgency_score += 0.1

        return min(1.0, urgency_score)

    def _calculate_sentiment(self, emotion: UserEmotion) -> float:
        """Calculate sentiment score (-1 to 1)."""
        emotion_sentiment = {
            UserEmotion.HAPPY: 0.7,
            UserEmotion.EXCITED: 0.9,
            UserEmotion.NEUTRAL: 0.0,
            UserEmotion.CURIOUS: 0.3,
            UserEmotion.CONFUSED: -0.2,
            UserEmotion.FRUSTRATED: -0.5,
            UserEmotion.ANGRY: -0.8,
            UserEmotion.SAD: -0.7,
            UserEmotion.ANXIOUS: -0.6,
            UserEmotion.PLAYFUL: 0.6,
        }
        return emotion_sentiment.get(emotion, 0.0)

    def _classify_conversation_type(self, intent: UserIntent) -> str:
        """Classify conversation type based on intent."""
        task_intents = [UserIntent.REQUEST_ACTION, UserIntent.TROUBLESHOOT, UserIntent.ASK_QUESTION]
        social_intents = [UserIntent.SMALL_TALK, UserIntent.JOKE, UserIntent.GREETING, UserIntent.GOODBYE]
        deep_intents = [UserIntent.PHILOSOPHICAL, UserIntent.VENT, UserIntent.SHARE_BAD_NEWS]

        if intent in task_intents:
            return "task"
        elif intent in social_intents:
            return "social"
        elif intent in deep_intents:
            return "deep"
        else:
            return "casual"
