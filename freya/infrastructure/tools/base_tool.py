"""Base tool interface and implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from freya.domain.exceptions import ToolExecutionError, ToolValidationError
from freya.shared.logging.decorators import log_async_performance
from freya.shared.logging.logger import get_logger


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Tools are capabilities that agents can invoke to perform actions.
    """

    def __init__(self, name: str, description: str) -> None:
        """
        Initialize tool.
        
        Args:
            name: Tool name (unique identifier)
            description: Human-readable description
        """
        self._name = name
        self._description = description
        self._logger = get_logger(__name__).bind(tool=name)

    @property
    def name(self) -> str:
        """Tool name."""
        return self._name

    @property
    def description(self) -> str:
        """Tool description."""
        return self._description

    @abstractmethod
    def get_parameters_schema(self) -> dict[str, Any]:
        """
        Get JSON schema for tool parameters.
        
        Returns:
            JSON schema dictionary
        """
        ...

    @log_async_performance(threshold_ms=5000)
    async def execute(self, **parameters: Any) -> Any:
        """
        Execute the tool with parameters.
        
        Args:
            **parameters: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            ToolValidationError: If parameters are invalid
            ToolExecutionError: If execution fails
        """
        # Validate parameters
        self._validate_parameters(parameters)

        # Execute tool-specific logic
        try:
            result = await self._execute_internal(**parameters)

            self._logger.info(
                "Tool executed successfully",
                parameters=str(parameters)[:100],
            )

            return result

        except Exception as e:
            self._logger.error(
                "Tool execution failed",
                error=str(e),
                parameters=str(parameters)[:100],
                exc_info=e,
            )
            raise ToolExecutionError(
                f"Tool {self._name} execution failed",
                tool_name=self._name,
                parameters=parameters,
                cause=e,
            ) from e

    @abstractmethod
    async def _execute_internal(self, **parameters: Any) -> Any:
        """
        Internal execution logic (implemented by subclasses).
        
        Args:
            **parameters: Validated parameters
            
        Returns:
            Execution result
        """
        ...

    def _validate_parameters(self, parameters: dict[str, Any]) -> None:
        """
        Validate parameters against schema.
        
        Args:
            parameters: Parameters to validate
            
        Raises:
            ToolValidationError: If validation fails
        """
        schema = self.get_parameters_schema()
        required = schema.get("required", [])

        # Check required parameters
        for param in required:
            if param not in parameters:
                raise ToolValidationError(
                    f"Missing required parameter: {param}",
                    tool_name=self._name,
                    parameter=param,
                )

        # Type checking could be added here
        # For now, we rely on runtime type checking

    def to_dict(self) -> dict[str, Any]:
        """Convert tool to dictionary representation."""
        return {
            "name": self._name,
            "description": self._description,
            "parameters": self.get_parameters_schema(),
        }


class ToolRegistry:
    """
    Registry for managing available tools.
    
    Singleton pattern for global tool access.
    """

    _instance: ToolRegistry | None = None

    def __new__(cls) -> ToolRegistry:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: dict[str, BaseTool] = {}
            cls._instance._logger = get_logger(__name__)
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool to register
        """
        self._tools[tool.name] = tool
        self._logger.info("Tool registered", tool_name=tool.name)

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            self._logger.info("Tool unregistered", tool_name=tool_name)

    def get(self, tool_name: str) -> BaseTool | None:
        """
        Get a tool by name.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def get_all(self) -> dict[str, BaseTool]:
        """Get all registered tools."""
        return self._tools.copy()

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all tools with their descriptions.
        
        Returns:
            List of tool dictionaries
        """
        return [tool.to_dict() for tool in self._tools.values()]
