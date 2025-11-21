"""
Personality Engine - Main coordinator for personality system.

Combines context analysis and personality adaptation into a single
synchronous interface for the orchestrator.
"""

from datetime import datetime
from typing import Optional

from .analyzer import ContextAnalyzer, UserEmotion, UserIntent
from .traits import (
    EmotionalState,
    MoodContext,
    PersonalityAdaptation,
    PersonalityMode,
    PersonalityTraits,
)


class PersonalityEngine:
    """
    Main personality coordinator.
    
    Analyzes user queries and generates personality instructions
    for the LLM to adapt its response style.
    """
    
    def __init__(self, config: dict):
        """
        Initialize personality engine.
        
        Args:
            config: Personality configuration dict with trait values
        """
        self.analyzer = ContextAnalyzer()
        self.traits = self._load_traits(config)
        self.mood = MoodContext()
        self._conversation_count = 0
        
    def _load_traits(self, config: dict) -> PersonalityTraits:
        """Load personality traits from config."""
        traits_config = config.get("traits", {})
        return PersonalityTraits(
            directness=traits_config.get("directness", 0.8),
            humor_level=traits_config.get("humor_level", 0.7),
            empathy=traits_config.get("empathy", 0.7),
            formality=traits_config.get("formality", 0.2),
            verbosity=traits_config.get("verbosity", 0.6),
            curiosity=traits_config.get("curiosity", 0.7),
            sassiness=traits_config.get("sassiness", 0.6),
            patience=traits_config.get("patience", 0.8),
        )
    
    def analyze_and_adapt(self, query: str, time_of_day: Optional[str] = None) -> str:
        """
        Analyze user query and generate personality instructions.
        
        Args:
            query: User's query text
            time_of_day: Optional time context ("morning", "afternoon", "evening", "night")
            
        Returns:
            Personality instruction string to inject into system prompt
        """
        # Analyze user query
        analysis = self.analyzer.analyze(query)
        
        # Update mood based on analysis
        self._update_mood(analysis, time_of_day)
        
        # Generate personality instructions
        instructions = PersonalityAdaptation.get_instructions(
            traits=self.traits,
            mood=self.mood,
            conversation_type=analysis.conversation_type,
            user_emotion=analysis.emotion.value,
            sentiment=analysis.sentiment,
            urgency=analysis.urgency,
        )
        
        # Increment conversation counter
        self._conversation_count += 1
        
        return instructions
    
    def _update_mood(self, analysis, time_of_day: Optional[str]):
        """Update mood state based on context analysis."""
        # Map user emotion to Freya's emotional response
        emotion_response_map = {
            UserEmotion.HAPPY: EmotionalState.HAPPY,
            UserEmotion.EXCITED: EmotionalState.EXCITED,
            UserEmotion.SAD: EmotionalState.EMPATHETIC,
            UserEmotion.ANXIOUS: EmotionalState.SUPPORTIVE,
            UserEmotion.FRUSTRATED: EmotionalState.EMPATHETIC,
            UserEmotion.ANGRY: EmotionalState.EMPATHETIC,
            UserEmotion.CONFUSED: EmotionalState.SUPPORTIVE,
            UserEmotion.CURIOUS: EmotionalState.CURIOUS,
            UserEmotion.PLAYFUL: EmotionalState.PLAYFUL,
            UserEmotion.NEUTRAL: EmotionalState.NEUTRAL,
        }
        
        new_state = emotion_response_map.get(analysis.emotion, EmotionalState.NEUTRAL)
        self.mood.set_emotional_state(new_state)
        
        # Map intent to personality mode
        intent_mode_map = {
            UserIntent.ASK_QUESTION: PersonalityMode.TEACHING,
            UserIntent.ASK_HELP: PersonalityMode.SUPPORTIVE,
            UserIntent.TROUBLESHOOT: PersonalityMode.PROFESSIONAL,
            UserIntent.SHARE_GOOD_NEWS: PersonalityMode.PLAYFUL,
            UserIntent.SHARE_BAD_NEWS: PersonalityMode.SUPPORTIVE,
            UserIntent.VENT: PersonalityMode.SUPPORTIVE,
            UserIntent.JOKE: PersonalityMode.PLAYFUL,
            UserIntent.PHILOSOPHICAL: PersonalityMode.DEEP,
            UserIntent.SMALL_TALK: PersonalityMode.CASUAL,
        }
        
        self.mood.mode = intent_mode_map.get(analysis.intent, PersonalityMode.CASUAL)
        
        # Adjust energy based on time of day
        if time_of_day:
            self._adjust_energy_for_time(time_of_day)
        
        # Track conversation depth
        if analysis.intent in [UserIntent.ASK_QUESTION, UserIntent.PHILOSOPHICAL]:
            self.mood.increment_depth()
        elif analysis.intent in [UserIntent.GREETING, UserIntent.SMALL_TALK]:
            self.mood.reset_depth()
        
        # Adjust energy based on user sentiment
        if analysis.sentiment > 0.5:
            self.mood.update_energy(0.1)  # User is happy, boost energy
        elif analysis.sentiment < -0.5:
            self.mood.update_energy(-0.1)  # User is upset, calm down
    
    def _adjust_energy_for_time(self, time_of_day: str):
        """Adjust energy level based on time of day."""
        time_energy = {
            "morning": 0.6,   # Fresh but not too energetic
            "afternoon": 0.8,  # Peak energy
            "evening": 0.5,   # Winding down
            "night": 0.4,     # Tired
        }
        
        target_energy = time_energy.get(time_of_day, 0.7)
        
        # Gradually adjust toward target
        current = self.mood.energy_level
        delta = (target_energy - current) * 0.2  # 20% adjustment
        self.mood.update_energy(delta)
    
    def get_state_summary(self) -> dict:
        """Get current personality state (for debugging/logging)."""
        return {
            "emotional_state": self.mood.emotional_state.value,
            "mode": self.mood.mode.value,
            "energy_level": round(self.mood.energy_level, 2),
            "conversation_depth": self.mood.conversation_depth,
            "conversation_count": self._conversation_count,
        }
    
    def reset(self):
        """Reset mood to neutral state (for new conversation)."""
        self.mood = MoodContext()
        self._conversation_count = 0


def get_time_of_day() -> str:
    """Helper to determine current time of day."""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"
