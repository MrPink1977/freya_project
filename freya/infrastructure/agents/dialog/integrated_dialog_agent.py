"""
Integrated Dialog Agent - Complete model architecture implementation.

Combines:
- ModelManager for smart model loading (16GB VRAM optimized)
- PersonalityWrapper for consistent output
- MemorySystem for context retrieval
- Smart routing between primary/reasoning/code/vision models
- Auto-escalation when primary model needs help

This is the production-ready version with all features integrated.
"""

import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum

from freya.infrastructure.agents.base.base_agent import BaseAgent
from freya.domain.value_objects.event import Event, EventType
from freya.domain.value_objects.message import Message, MessageRole
from freya.infrastructure.models.model_manager import ModelManager, ModelType
from freya.infrastructure.personality.personality_wrapper import PersonalityWrapper
from freya.infrastructure.memory.memory_system import MemorySystem
from freya.domain.entities.memory import MemoryType
from freya.domain.interfaces.message_bus import IMessageBus
from freya.shared.logging.logger import get_logger
from freya.shared.logging.decorators import log_performance, log_async_errors


logger = get_logger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CODE = "code"
    VISION = "vision"
    MEMORY = "memory"


class IntegratedDialogAgent(BaseAgent):
    """
    Production-ready dialog agent with complete model architecture.
    
    Features:
    - Smart model selection based on query complexity
    - Auto-escalation from primary to reasoning model
    - Personality filtering for all specialist outputs
    - Memory-augmented responses
    - Optimized for 16GB VRAM
    
    Model flow:
    1. Analyze query complexity
    2. Check if memory context needed
    3. Route to appropriate model (primary/reasoning/code/vision)
    4. Filter output through personality wrapper
    5. Store interaction in memory
    """
    
    def __init__(
        self,
        message_bus: IMessageBus,
        model_manager: ModelManager,
        memory_system: MemorySystem,
    ):
        """
        Initialize integrated dialog agent.
        
        Args:
            message_bus: Message bus for events
            model_manager: Model manager for loading models
            memory_system: Memory system for context
        """
        super().__init__("integrated_dialog_agent", message_bus)
        
        self.model_manager = model_manager
        self.memory_system = memory_system
        
        # Will be initialized in start()
        self.primary_model = None
        self.personality_wrapper = None
        
        logger.info("IntegratedDialogAgent initialized")
    
    async def start(self):
        """Start the agent and load essential models."""
        await super().start()
        
        # Load primary model (always loaded)
        self.primary_model = await self.model_manager.get_model(ModelType.PRIMARY)
        
        # Initialize personality wrapper
        self.personality_wrapper = PersonalityWrapper(self.primary_model)
        
        logger.info("IntegratedDialogAgent started with primary model loaded")
    
    def subscribes_to(self) -> List[str]:
        """Event subscriptions."""
        return [
            EventType.DIALOG_REQUEST,
            "dialog.clear_context",
        ]
    
    @log_async_errors()
    async def _handle_event_internal(self, event: Event) -> None:
        """Route events to handlers."""
        if event.event_type == EventType.DIALOG_REQUEST:
            await self._handle_dialog_request(event)
        elif event.event_type == "dialog.clear_context":
            await self._handle_clear_context(event)
    
    @log_performance
    async def _handle_dialog_request(self, event: Event) -> None:
        """
        Handle dialog request with complete model architecture.
        
        Flow:
        1. Extract user query
        2. Analyze complexity
        3. Retrieve relevant memories
        4. Route to appropriate model
        5. Filter through personality
        6. Store in memory
        7. Publish response
        """
        try:
            # Extract request data
            user_text = event.data.get("text", "")
            if not user_text:
                raise ValueError("Missing 'text' in dialog request")
            
            stream = event.data.get("stream", True)
            correlation_id = event.correlation_id
            
            logger.info(
                f"Processing dialog request: {user_text[:50]}...",
                extra={"query_length": len(user_text), "stream": stream}
            )
            
            # 1. Analyze query complexity
            complexity = await self._analyze_complexity(user_text)
            logger.info(f"Query complexity: {complexity.value}")
            
            # 2. Retrieve relevant memories
            memories = await self._retrieve_memories(user_text)
            logger.info(f"Retrieved {len(memories)} relevant memories")
            
            # 3. Build context with memories
            messages = self._build_messages(user_text, memories)
            
            # 4. Route to appropriate model and generate
            if complexity == QueryComplexity.SIMPLE:
                response = await self._generate_simple(messages, user_text)
            elif complexity == QueryComplexity.COMPLEX:
                response = await self._generate_with_reasoning(messages, user_text)
            elif complexity == QueryComplexity.CODE:
                response = await self._generate_code(messages, user_text)
            elif complexity == QueryComplexity.VISION:
                response = await self._generate_vision(messages, user_text, event.data)
            elif complexity == QueryComplexity.MEMORY:
                response = await self._generate_memory_response(memories, user_text)
            else:
                response = await self._generate_simple(messages, user_text)
            
            # 5. Store interaction in memory
            await self._store_interaction(user_text, response)
            
            # 6. Publish response
            await self.publish_event(
                event_type=EventType.DIALOG_COMPLETE,
                data={
                    "response": response,
                    "complexity": complexity.value,
                    "memory_count": len(memories),
                },
                correlation_id=correlation_id,
            )
            
            logger.info("Dialog request completed successfully")
            
        except Exception as e:
            logger.error(f"Dialog request failed: {e}", exc_info=True)
            await self.publish_event(
                event_type=EventType.DIALOG_ERROR,
                data={"error": str(e)},
                correlation_id=event.correlation_id,
            )
    
    async def _analyze_complexity(self, query: str) -> QueryComplexity:
        """
        Analyze query complexity to determine routing.
        
        Args:
            query: User query
            
        Returns:
            Query complexity level
        """
        query_lower = query.lower()
        
        # Check for memory queries
        memory_keywords = ["remember", "told you", "said about", "mentioned", "recall"]
        if any(kw in query_lower for kw in memory_keywords):
            return QueryComplexity.MEMORY
        
        # Check for code queries
        code_keywords = ["code", "function", "program", "debug", "implement", "algorithm"]
        if any(kw in query_lower for kw in code_keywords):
            return QueryComplexity.CODE
        
        # Check for vision queries (would need image in event data)
        vision_keywords = ["see", "look", "image", "picture", "photo", "show"]
        if any(kw in query_lower for kw in vision_keywords):
            return QueryComplexity.VISION
        
        # Check for complex reasoning
        complex_keywords = ["why", "explain", "analyze", "compare", "evaluate", "philosophy"]
        if any(kw in query_lower for kw in complex_keywords):
            return QueryComplexity.COMPLEX
        
        # Check query length (longer queries often more complex)
        if len(query.split()) > 30:
            return QueryComplexity.COMPLEX
        
        # Default: simple
        return QueryComplexity.SIMPLE
    
    async def _retrieve_memories(self, query: str, top_k: int = 5) -> List:
        """
        Retrieve relevant memories for context.
        
        Args:
            query: User query
            top_k: Number of memories to retrieve
            
        Returns:
            List of relevant memories
        """
        try:
            results = self.memory_system.search(query, top_k=top_k)
            return [r.memory for r in results if r.similarity > 0.7]
        except Exception as e:
            logger.warning(f"Failed to retrieve memories: {e}")
            return []
    
    def _build_messages(self, query: str, memories: List) -> List[Dict]:
        """
        Build message list with memory context.
        
        Args:
            query: User query
            memories: Relevant memories
            
        Returns:
            List of messages for LLM
        """
        messages = []
        
        # Add memory context if available
        if memories:
            context_parts = ["Here's what I remember that might be relevant:\n"]
            for memory in memories[:3]:  # Limit to top 3
                context_parts.append(f"- {memory.content}")
            
            context = "\n".join(context_parts)
            messages.append({
                "role": "system",
                "content": f"Context from memory:\n{context}"
            })
        
        # Add user query
        messages.append({
            "role": "user",
            "content": query
        })
        
        return messages
    
    async def _generate_simple(self, messages: List[Dict], query: str) -> str:
        """
        Generate response using primary model (simple queries).
        
        Args:
            messages: Message history
            query: User query
            
        Returns:
            Generated response
        """
        logger.info("Using primary model for simple query")
        
        response = await self.primary_model.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        # Extract text
        if isinstance(response, dict):
            return response.get('content', response.get('text', str(response)))
        return str(response)
    
    async def _generate_with_reasoning(self, messages: List[Dict], query: str) -> str:
        """
        Generate response using reasoning model with personality filtering.
        
        Args:
            messages: Message history
            query: User query
            
        Returns:
            Personality-filtered response
        """
        logger.info("Using reasoning model for complex query")
        
        # Load reasoning model
        reasoning_model = await self.model_manager.get_model(ModelType.REASONING)
        
        # Generate with reasoning model
        raw_response = await reasoning_model.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        
        # Extract text
        if isinstance(raw_response, dict):
            raw_text = raw_response.get('content', raw_response.get('text', str(raw_response)))
        else:
            raw_text = str(raw_response)
        
        # Filter through personality wrapper
        friendly_response = await self.personality_wrapper.wrap(
            content=raw_text,
            original_query=query,
            source_model="reasoning"
        )
        
        return friendly_response
    
    async def _generate_code(self, messages: List[Dict], query: str) -> str:
        """
        Generate code response with personality filtering.
        
        Args:
            messages: Message history
            query: User query
            
        Returns:
            Personality-filtered code response
        """
        logger.info("Using code model for programming query")
        
        # Load code model
        code_model = await self.model_manager.get_model(ModelType.CODE)
        
        # Generate with code model
        raw_response = await code_model.generate(
            messages=messages,
            temperature=0.3,  # Lower temperature for code
            max_tokens=2000,
        )
        
        # Extract text
        if isinstance(raw_response, dict):
            raw_text = raw_response.get('content', raw_response.get('text', str(raw_response)))
        else:
            raw_text = str(raw_response)
        
        # Filter through personality wrapper (preserves code blocks)
        friendly_response = await self.personality_wrapper.wrap_with_code_preservation(
            content=raw_text,
            original_query=query,
            source_model="code"
        )
        
        return friendly_response
    
    async def _generate_vision(self, messages: List[Dict], query: str, data: Dict) -> str:
        """
        Generate vision response with personality filtering.
        
        Args:
            messages: Message history
            query: User query
            data: Event data (may contain image)
            
        Returns:
            Personality-filtered vision response
        """
        logger.info("Using vision model for image query")
        
        # Load vision model
        vision_model = await self.model_manager.get_model(ModelType.VISION)
        
        # Add image to messages if provided
        image_url = data.get("image_url")
        if image_url:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
        
        # Generate with vision model
        raw_response = await vision_model.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        # Extract text
        if isinstance(raw_response, dict):
            raw_text = raw_response.get('content', raw_response.get('text', str(raw_response)))
        else:
            raw_text = str(raw_response)
        
        # Filter through personality wrapper
        friendly_response = await self.personality_wrapper.wrap(
            content=raw_text,
            original_query=query,
            source_model="vision"
        )
        
        return friendly_response
    
    async def _generate_memory_response(self, memories: List, query: str) -> str:
        """
        Generate response based on memories.
        
        Args:
            memories: Retrieved memories
            query: User query
            
        Returns:
            Synthesized response from memories
        """
        logger.info(f"Generating memory-based response from {len(memories)} memories")
        
        if not memories:
            return "I don't recall anything about that, sweetie. Could you remind me? 😊"
        
        # Build context from memories
        memory_texts = [m.content for m in memories]
        context = "\n".join(f"- {text}" for text in memory_texts[:5])
        
        # Use primary model to synthesize
        messages = [
            {
                "role": "system",
                "content": "You are Freya. The user is asking about something from memory. Use the provided memories to answer warmly and accurately."
            },
            {
                "role": "user",
                "content": f"Memories:\n{context}\n\nUser question: {query}\n\nAnswer based on these memories:"
            }
        ]
        
        response = await self.primary_model.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        # Extract text
        if isinstance(response, dict):
            return response.get('content', response.get('text', str(response)))
        return str(response)
    
    async def _store_interaction(self, query: str, response: str):
        """
        Store interaction in memory.
        
        Args:
            query: User query
            response: Agent response
        """
        try:
            # Store user query
            self.memory_system.store(
                text=f"User asked: {query}",
                memory_type=MemoryType.CONVERSATION,
                metadata={"role": "user"}
            )
            
            # Store agent response
            self.memory_system.store(
                text=f"I responded: {response}",
                memory_type=MemoryType.CONVERSATION,
                metadata={"role": "assistant"}
            )
            
            logger.debug("Interaction stored in memory")
            
        except Exception as e:
            logger.warning(f"Failed to store interaction: {e}")
    
    async def _handle_clear_context(self, event: Event):
        """Clear conversation context and memory."""
        try:
            user_id = event.data.get("user_id")
            self.memory_system.clear(user_id=user_id)
            logger.info(f"Cleared context for user: {user_id or 'all'}")
        except Exception as e:
            logger.error(f"Failed to clear context: {e}")
