"""Model selector service for choosing appropriate LLM models."""

from __future__ import annotations

import re
from typing import Any

from freya.domain.value_objects.message import Message
from freya.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ModelSelector:
    """
    Selects appropriate LLM model based on query characteristics.
    
    Strategy pattern for model selection.
    """

    def __init__(
        self,
        default_model: str = "llama3.2:3b",
        reasoning_model: str = "dolphin-mixtral:8x7b",
        code_model: str = "deepseek-coder-v2:16b-lite",
        enable_auto_selection: bool = True,
    ) -> None:
        """
        Initialize model selector.
        
        Args:
            default_model: Fast model for simple queries
            reasoning_model: Advanced model for complex reasoning
            code_model: Specialized model for code tasks
            enable_auto_selection: Enable automatic model selection
        """
        self._models = {
            "default": default_model,
            "reasoning": reasoning_model,
            "code": code_model,
        }
        self._enable_auto_selection = enable_auto_selection

        # Patterns for detecting query types
        self._code_patterns = [
            r"\bcode\b",
            r"\bfunction\b",
            r"\bclass\b",
            r"\bpython\b",
            r"\bjavascript\b",
            r"\bprogram\b",
            r"\bdebug\b",
            r"\berror\b.*\bcode\b",
        ]

        self._reasoning_patterns = [
            r"\bexplain\b.*\bwhy\b",
            r"\bcompare\b",
            r"\banalyze\b",
            r"\bwhat if\b",
            r"\bpros and cons\b",
            r"\badvantages and disadvantages\b",
            r"\breason\b",
            r"\blogic\b",
        ]

    async def select_model(
        self,
        user_text: str,
        messages: list[Message] | None = None,
        override_model: str | None = None,
    ) -> str:
        """
        Select appropriate model for the query.
        
        Args:
            user_text: User's query text
            messages: Conversation context (optional)
            override_model: Manual model override
            
        Returns:
            Selected model name
        """
        # Override takes precedence
        if override_model:
            logger.info("Using override model", model=override_model)
            return override_model

        # Auto-selection disabled
        if not self._enable_auto_selection:
            return self._models["default"]

        # Detect query type
        query_type = self._detect_query_type(user_text)

        # Select model based on type
        if query_type == "code":
            selected = self._models["code"]
        elif query_type == "reasoning":
            selected = self._models["reasoning"]
        else:
            selected = self._models["default"]

        logger.info(
            "Model selected",
            model=selected,
            query_type=query_type,
            auto_selected=True,
        )

        return selected

    def _detect_query_type(self, text: str) -> str:
        """
        Detect query type from text.
        
        Args:
            text: Query text
            
        Returns:
            Query type: "code", "reasoning", or "general"
        """
        text_lower = text.lower()

        # Check for code-related queries
        for pattern in self._code_patterns:
            if re.search(pattern, text_lower):
                return "code"

        # Check for reasoning queries
        for pattern in self._reasoning_patterns:
            if re.search(pattern, text_lower):
                return "reasoning"

        # Default to general
        return "general"

    def get_available_models(self) -> dict[str, str]:
        """Get available models."""
        return self._models.copy()

    def set_model(self, model_type: str, model_name: str) -> None:
        """
        Set a model.
        
        Args:
            model_type: Model type (default, reasoning, code)
            model_name: Model name
        """
        if model_type not in self._models:
            raise ValueError(f"Invalid model type: {model_type}")

        self._models[model_type] = model_name
        logger.info("Model updated", model_type=model_type, model_name=model_name)
