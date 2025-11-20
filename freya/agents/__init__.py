"""Agent package initialization."""

from freya.agents.base_agent import AgentCapability, AgentState, BaseAgent
from freya.agents.speech_agent import SpeechAgent

__all__ = ["BaseAgent", "AgentState", "AgentCapability", "SpeechAgent"]
