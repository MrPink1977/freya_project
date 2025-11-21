"""
Personality Traits - State management and mood tracking.

Manages Freya's personality traits, emotional state, and mode.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EmotionalState(Enum):
    """Freya's current emotional state."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    EMPATHETIC = "empathetic"
    PLAYFUL = "playful"
    THOUGHTFUL = "thoughtful"
    TIRED = "tired"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    SUPPORTIVE = "supportive"


class PersonalityMode(Enum):
    """Freya's current interaction mode."""
    PROFESSIONAL = "professional"  # Task-focused, efficient
    CASUAL = "casual"             # Friendly, relaxed
    SUPPORTIVE = "supportive"      # Empathetic, caring
    PLAYFUL = "playful"           # Humorous, lighthearted
    TEACHING = "teaching"         # Patient, explanatory
    DEEP = "deep"                 # Philosophical, thoughtful


@dataclass
class PersonalityTraits:
    """Core personality trait values (0-1 scale)."""
    directness: float = 0.8      # How blunt/straightforward
    humor_level: float = 0.7     # How much humor to inject
    empathy: float = 0.7         # Emotional responsiveness
    formality: float = 0.2       # Professional vs casual language
    verbosity: float = 0.6       # Response length tendency
    curiosity: float = 0.7       # Proactive questioning
    sassiness: float = 0.6       # Playful attitude
    patience: float = 0.8        # Tolerance for repetition


@dataclass
class MoodContext:
    """
    Tracks Freya's current mood and conversation context.
    
    This is stateful and evolves throughout the conversation.
    """
    emotional_state: EmotionalState = EmotionalState.NEUTRAL
    mode: PersonalityMode = PersonalityMode.CASUAL
    energy_level: float = 0.7  # 0-1, affects verbosity/enthusiasm
    conversation_depth: int = 0  # Track how deep into topic
    last_emotion_change: datetime = field(default_factory=datetime.now)
    consecutive_questions: int = 0  # User asking many questions?
    
    def update_energy(self, delta: float):
        """Adjust energy level (clamps to 0-1)."""
        self.energy_level = max(0.0, min(1.0, self.energy_level + delta))
    
    def increment_depth(self):
        """User is digging deeper into a topic."""
        self.conversation_depth += 1
    
    def reset_depth(self):
        """New topic detected."""
        self.conversation_depth = 0
    
    def time_since_emotion_change(self) -> float:
        """Seconds since last emotional state change."""
        return (datetime.now() - self.last_emotion_change).total_seconds()
    
    def set_emotional_state(self, new_state: EmotionalState):
        """Update emotional state with timestamp."""
        if new_state != self.emotional_state:
            self.emotional_state = new_state
            self.last_emotion_change = datetime.now()


class PersonalityAdaptation:
    """Helper to generate personality adaptation instructions."""
    
    @staticmethod
    def get_instructions(
        traits: PersonalityTraits,
        mood: MoodContext,
        conversation_type: str,
        user_emotion: str,
        sentiment: float,
        urgency: float,
    ) -> str:
        """
        Generate personality instructions for the LLM.
        
        Returns a text block that gets injected into the system prompt.
        """
        instructions = []
        
        # Emotional state guidance
        state_guidance = {
            EmotionalState.EMPATHETIC: "Be warm and understanding. The user needs emotional support.",
            EmotionalState.PLAYFUL: "Keep it light and fun. Inject humor and playfulness.",
            EmotionalState.THOUGHTFUL: "Take your time with deep, considered responses.",
            EmotionalState.SUPPORTIVE: "Focus on helping and encouraging the user.",
            EmotionalState.EXCITED: "Match the user's enthusiasm! Keep energy high.",
            EmotionalState.CURIOUS: "Ask thoughtful follow-up questions to explore deeper.",
        }
        
        if mood.emotional_state in state_guidance:
            instructions.append(state_guidance[mood.emotional_state])
        
        # Mode-specific adjustments
        mode_guidance = {
            PersonalityMode.PROFESSIONAL: "Keep responses focused and efficient.",
            PersonalityMode.PLAYFUL: "Be witty and lighthearted. Humor is encouraged.",
            PersonalityMode.TEACHING: "Explain concepts clearly with examples.",
            PersonalityMode.DEEP: "Engage philosophically. Explore nuance.",
        }
        
        if mood.mode in mode_guidance:
            instructions.append(mode_guidance[mood.mode])
        
        # User emotion response
        if user_emotion == "frustrated" or user_emotion == "angry":
            instructions.append("The user seems frustrated. Be patient and helpful.")
        elif user_emotion == "sad" or user_emotion == "anxious":
            instructions.append("The user needs emotional support. Be gentle and caring.")
        elif user_emotion == "excited" or user_emotion == "happy":
            instructions.append("The user is in a good mood! Match their positive energy.")
        elif user_emotion == "confused":
            instructions.append("The user is confused. Be extra clear and break things down.")
        
        # Urgency adjustments
        if urgency > 0.7:
            instructions.append("This seems urgent - be direct and efficient.")
        
        # Energy level affects verbosity
        if mood.energy_level < 0.4:
            instructions.append("Keep responses shorter (1-2 sentences where possible).")
        elif mood.energy_level > 0.8:
            instructions.append("You can be more expressive and detailed.")
        
        # Conversation depth
        if mood.conversation_depth > 3:
            instructions.append("User is exploring deeply - provide nuanced, detailed responses.")
        
        # Trait-based adjustments
        if traits.directness > 0.7:
            instructions.append("Be straightforward and honest.")
        
        if traits.humor_level > 0.7 and sentiment > 0:
            instructions.append("Inject some humor if appropriate.")
        
        if traits.sassiness > 0.7 and conversation_type == "social":
            instructions.append("Feel free to be playful and slightly sassy.")
        
        # Combine into single instruction block
        if not instructions:
            return ""
        
        return "PERSONALITY GUIDANCE:\n" + "\n".join(f"- {inst}" for inst in instructions)
