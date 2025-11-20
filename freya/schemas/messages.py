"""
Pydantic schemas for agent message payloads.

Validates structure, types, and constraints for messages passed between
agents via the message bus. Catches type confusion, range violations,
and malformed data before it reaches business logic.
"""
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


class DialogRequestPayload(BaseModel):
    """Payload for dialog.request messages to DialogAgent."""
    
    text: str = Field(min_length=1, max_length=5000, description="User input text")
    model: Optional[str] = Field(None, max_length=100, description="Override LLM model")
    stream: bool = Field(True, description="Enable streaming response")


class MemoryStorePayload(BaseModel):
    """Payload for memory.store messages to MemoryAgent."""
    
    content: str = Field(min_length=1, max_length=10000, description="Memory content to store")
    role: Literal["user", "assistant"] = Field("user", description="Speaker role")
    importance: int = Field(1, ge=1, le=10, description="Memory importance ranking")
    
    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        """Remove leading/trailing whitespace from content."""
        return v.strip()


class MemoryQueryPayload(BaseModel):
    """Payload for memory.query messages to MemoryAgent."""
    
    query: str = Field(min_length=1, max_length=500, description="Search query text")
    limit: int = Field(3, ge=1, le=50, description="Maximum results to return")
    min_score: float = Field(0.2, ge=0.0, le=1.0, description="Minimum similarity score")
    filter: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filter")
    
    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        """Remove leading/trailing whitespace from query."""
        return v.strip()


class FactStorePayload(BaseModel):
    """Payload for memory.fact.store messages to MemoryAgent."""
    
    category: str = Field(min_length=1, max_length=100, description="Fact category (name, birthday, etc)")
    key: str = Field(min_length=1, max_length=100, description="Fact key identifier")
    value: str = Field(min_length=1, max_length=1000, description="Fact value")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    
    @field_validator("category", "key", "value")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        """Remove leading/trailing whitespace."""
        return v.strip()


class FactQueryPayload(BaseModel):
    """Payload for memory.fact.query messages to MemoryAgent."""
    
    query: str = Field(min_length=1, max_length=500, description="Fact search query")
    category: Optional[str] = Field(None, max_length=100, description="Filter by category")
    limit: int = Field(3, ge=1, le=50, description="Maximum results")
    
    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        """Remove leading/trailing whitespace from query."""
        return v.strip()
    
    @field_validator("category")
    @classmethod
    def strip_category(cls, v: Optional[str]) -> Optional[str]:
        """Remove leading/trailing whitespace from category."""
        return v.strip() if v else None


class UserQueryPayload(BaseModel):
    """Payload for user.query messages to ToolExecutorAgent."""
    
    text: str = Field(min_length=1, max_length=5000, description="User query text")
    
    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        """Remove leading/trailing whitespace from text."""
        return v.strip()


class SpeakRequestPayload(BaseModel):
    """Payload for speech.speak messages to SpeechAgent."""
    
    text: str = Field(min_length=1, max_length=5000, description="Text to speak")
    channel_id: str = Field("pc", pattern=r'^[a-zA-Z0-9_-]+$', description="Audio channel ID")
    
    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        """Remove leading/trailing whitespace from text."""
        return v.strip()


class ListenRequestPayload(BaseModel):
    """Payload for speech.listen messages to SpeechAgent."""
    
    channel_id: str = Field("pc", pattern=r'^[a-zA-Z0-9_-]+$', description="Audio channel ID")
    timeout: float = Field(30.0, gt=0.0, le=120.0, description="Listen timeout in seconds")
