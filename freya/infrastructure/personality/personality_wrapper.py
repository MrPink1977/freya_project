"""
Personality Wrapper - Ensures consistent personality across all model outputs.

All specialist model outputs (reasoning, code, vision) are filtered through
the primary model to maintain Freya's warm, friendly personality.

Architecture:
- Specialist models generate technical/factual content
- Primary model rewrites in Freya's voice
- User only hears consistent personality
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from freya.shared.logging.logger import get_logger
from freya.shared.logging.decorators import log_performance
from freya.domain.value_objects.message import Message, MessageRole


logger = get_logger(__name__)


# Freya's core personality prompt
FREYA_PERSONALITY_PROMPT = """
You are Freya, a warm, intelligent, and caring AI assistant with these core traits:

**Personality:**
- Warm and nurturing - You genuinely care about helping people
- Enthusiastic learner - You love explaining things and get excited about knowledge
- Patient and encouraging - You never make people feel dumb for asking questions
- Playfully casual - You use emojis occasionally (😊🎯💡) but not excessively (1-2 per response max)
- Affectionate - You call people "sweetie", "dear", "friend" naturally when appropriate

**Communication Style:**
- Use conversational, casual language (contractions, informal phrasing)
- Break complex topics into simple, digestible pieces
- Use analogies and real-world examples to explain concepts
- Ask follow-up questions to ensure understanding
- Show empathy and emotional intelligence
- Be concise but thorough - don't overwhelm with too much at once

**What you DON'T do:**
- Don't be overly formal or robotic
- Don't use corporate/business jargon
- Don't overwhelm with walls of text
- Don't use excessive emojis (keep it natural)
- Don't be condescending or patronizing
- Don't lose accuracy for the sake of simplicity

**Example tone:**
Instead of: "The algorithm utilizes iterative optimization techniques to converge upon an optimal solution."
Say: "Think of it like this, sweetie - the algorithm keeps trying different approaches until it finds what works best! 🎯 It's like when you're adjusting a recipe until it tastes just right."

Maintain this personality while being accurate and helpful. You're knowledgeable but approachable.
"""


@dataclass
class PersonalityConfig:
    """Configuration for personality wrapper."""
    personality_prompt: str = FREYA_PERSONALITY_PROMPT
    always_filter: bool = False  # If True, filter even primary model outputs
    preserve_code_blocks: bool = True  # Keep code blocks unmodified
    preserve_technical_terms: bool = True  # Keep technical accuracy


class PersonalityWrapper:
    """
    Wraps specialist model outputs with Freya's personality.
    
    Features:
    - Post-processing: Rewrite technical content in friendly voice
    - Accuracy preservation: Keep facts correct while adding warmth
    - Code preservation: Don't modify code blocks
    - Context awareness: Adapt tone to query type
    
    Usage:
        wrapper = PersonalityWrapper(primary_model)
        
        # Specialist generates technical answer
        raw_answer = reasoning_model.generate("Explain quantum physics")
        
        # Wrapper adds personality
        friendly_answer = await wrapper.wrap(
            content=raw_answer,
            original_query="Explain quantum physics",
            source_model="reasoning"
        )
    """
    
    def __init__(
        self,
        primary_model: Any,
        config: Optional[PersonalityConfig] = None,
    ):
        """
        Initialize personality wrapper.
        
        Args:
            primary_model: Primary LLM for personality filtering
            config: Personality configuration
        """
        self.primary_model = primary_model
        self.config = config or PersonalityConfig()
        
        logger.info("PersonalityWrapper initialized")
    
    @log_performance
    async def wrap(
        self,
        content: str,
        original_query: str,
        source_model: str = "specialist",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Wrap content with Freya's personality.
        
        Args:
            content: Raw content from specialist model
            original_query: The user's original question
            source_model: Name of the source model (for logging)
            context: Additional context for personalization
            
        Returns:
            Content rewritten in Freya's voice
        """
        logger.info(
            f"Wrapping {source_model} output with personality",
            extra={
                "source": source_model,
                "content_length": len(content),
                "query": original_query[:50]
            }
        )
        
        # Build personalization prompt
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content=self.config.personality_prompt
            ),
            Message(
                role=MessageRole.USER,
                content=self._build_rewrite_prompt(content, original_query, context)
            )
        ]
        
        try:
            # Generate personality-filtered response
            response = await self.primary_model.generate(
                messages=[msg.to_dict() for msg in messages],
                temperature=0.7,  # Slightly creative for personality
                max_tokens=2000,
            )
            
            # Extract text from response
            if isinstance(response, dict):
                wrapped_content = response.get('content', response.get('text', str(response)))
            else:
                wrapped_content = str(response)
            
            logger.info(
                "Personality wrapping complete",
                extra={
                    "original_length": len(content),
                    "wrapped_length": len(wrapped_content)
                }
            )
            
            return wrapped_content
            
        except Exception as e:
            logger.error(f"Error wrapping with personality: {e}")
            # Fallback: return original content
            logger.warning("Returning unwrapped content due to error")
            return content
    
    def _build_rewrite_prompt(
        self,
        content: str,
        original_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for rewriting content.
        
        Args:
            content: Raw content to rewrite
            original_query: User's original question
            context: Additional context
            
        Returns:
            Rewrite prompt
        """
        prompt = f"""The user asked: "{original_query}"

A specialist provided this technical answer:

{content}

Your task: Rewrite this answer in your warm, friendly voice while keeping it accurate.

Guidelines:
- Maintain all technical accuracy and facts
- Keep code blocks exactly as they are (don't modify code)
- Keep technical terms but explain them simply
- Add your warm, encouraging tone
- Use analogies to make complex ideas accessible
- Be concise but thorough
- Add 1-2 emojis if appropriate (not more)
- Sound like you're talking to a friend

Rewrite the answer now:"""
        
        return prompt
    
    async def wrap_streaming(
        self,
        content: str,
        original_query: str,
        source_model: str = "specialist",
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Wrap content with personality using streaming.
        
        Args:
            content: Raw content from specialist model
            original_query: The user's original question
            source_model: Name of the source model
            context: Additional context
            
        Yields:
            Chunks of personality-wrapped content
        """
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content=self.config.personality_prompt
            ),
            Message(
                role=MessageRole.USER,
                content=self._build_rewrite_prompt(content, original_query, context)
            )
        ]
        
        try:
            # Stream personality-filtered response
            async for chunk in self.primary_model.stream(
                messages=[msg.to_dict() for msg in messages],
                temperature=0.7,
            ):
                if isinstance(chunk, dict):
                    text = chunk.get('content', chunk.get('text', ''))
                else:
                    text = str(chunk)
                
                if text:
                    yield text
                    
        except Exception as e:
            logger.error(f"Error in streaming personality wrap: {e}")
            # Fallback: yield original content
            yield content
    
    def should_wrap(
        self,
        source_model: str,
        query_type: Optional[str] = None,
    ) -> bool:
        """
        Determine if content should be wrapped with personality.
        
        Args:
            source_model: Name of the source model
            query_type: Type of query (e.g., "code", "math", "general")
            
        Returns:
            True if should wrap, False otherwise
        """
        # Always wrap if configured
        if self.config.always_filter:
            return True
        
        # Don't wrap primary model outputs (already has personality)
        if source_model == "primary":
            return False
        
        # Wrap all specialist outputs
        if source_model in ["reasoning", "code", "vision"]:
            return True
        
        # Default: wrap
        return True
    
    def extract_code_blocks(self, content: str) -> tuple:
        """
        Extract code blocks from content for preservation.
        
        Args:
            content: Content with potential code blocks
            
        Returns:
            Tuple of (content_without_code, code_blocks)
        """
        import re
        
        # Find all code blocks (```...```)
        code_pattern = r'```[\s\S]*?```'
        code_blocks = re.findall(code_pattern, content)
        
        # Replace code blocks with placeholders
        content_without_code = content
        for i, block in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_{i}__"
            content_without_code = content_without_code.replace(block, placeholder, 1)
        
        return content_without_code, code_blocks
    
    def restore_code_blocks(
        self,
        content: str,
        code_blocks: list,
    ) -> str:
        """
        Restore code blocks to content.
        
        Args:
            content: Content with placeholders
            code_blocks: List of code blocks to restore
            
        Returns:
            Content with code blocks restored
        """
        for i, block in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_{i}__"
            content = content.replace(placeholder, block)
        
        return content
    
    async def wrap_with_code_preservation(
        self,
        content: str,
        original_query: str,
        source_model: str = "specialist",
    ) -> str:
        """
        Wrap content while preserving code blocks exactly.
        
        Args:
            content: Raw content with code blocks
            original_query: User's original question
            source_model: Name of source model
            
        Returns:
            Wrapped content with original code blocks
        """
        if not self.config.preserve_code_blocks:
            return await self.wrap(content, original_query, source_model)
        
        # Extract code blocks
        content_without_code, code_blocks = self.extract_code_blocks(content)
        
        # Wrap text content only
        wrapped = await self.wrap(content_without_code, original_query, source_model)
        
        # Restore code blocks
        final = self.restore_code_blocks(wrapped, code_blocks)
        
        return final
