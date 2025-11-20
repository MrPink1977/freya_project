"""
TOOL EXECUTOR AGENT - Detects and executes tools based on user queries.

Extracts tool execution logic from orchestrator for better modularity.
"""

from __future__ import annotations

import re
from typing import Optional

from freya.agents.base_agent import AgentCapability, BaseAgent
from freya.core.message_bus import Message, MessageBus, MessagePriority
from freya.exceptions import AgentMessageError
from freya.schemas.messages import UserQueryPayload
from freya.schemas.validation import validate_message_payload
from freya.tools.manager import ToolManager


class ToolExecutorAgent(BaseAgent):
    """
    Agent that detects tool requirements in user queries and executes them.

    Subscribes to: "user.query"
    Publishes to: "tool.result", "tool.not_found"
    """

    def __init__(self, agent_id: str, bus: MessageBus, tool_manager: ToolManager) -> None:
        """
        Initialize tool executor agent.

        Args:
            agent_id: Unique agent identifier
            bus: Message bus for communication
            tool_manager: Existing ToolManager instance
        """
        super().__init__(agent_id, bus)
        self.tool_manager = tool_manager

        # Tool detection patterns (from orchestrator._try_tool_execution)
        self._tool_patterns = {
            "time": re.compile(
                r"\b(what\s+time|current\s+time|time\s+is\s+it|tell.*time)\b",
                re.IGNORECASE,
            ),
            "date": re.compile(
                r"\b(what.*date|today'?s?\s+date|current\s+date|what\s+day)\b",
                re.IGNORECASE,
            ),
            "calculate": re.compile(
                r"\b(calculate|compute|what\s+is|how\s+much|math|plus|minus|times|divided)\b",
                re.IGNORECASE,
            ),
            "files": re.compile(
                r"\b(list\s+files|show\s+files|files\s+in|directory|folder)\b",
                re.IGNORECASE,
            ),
            "read_file": re.compile(
                r"\b(read|show|open|display)\s+(file|the\s+file)\b", re.IGNORECASE
            ),
            "write_file": re.compile(r"\b(write|create|save)\s+(to\s+)?file\b", re.IGNORECASE),
            "system": re.compile(
                r"\b(system\s+info|os\s+info|python\s+version|disk\s+space)\b",
                re.IGNORECASE,
            ),
            "performance": re.compile(
                r"\b(cpu\s+usage|memory\s+usage|performance|gpu\s+usage|task\s+manager|"
                r"resource\s+usage|system\s+performance)\b",
                re.IGNORECASE,
            ),
            "web_search": re.compile(
                r"\b(search\s+(the\s+)?web|google|look\s+up|find\s+online)\b",
                re.IGNORECASE,
            ),
        }

    async def initialize(self) -> None:
        """Initialize tool executor agent."""
        self.logger.info(
            f"ToolExecutorAgent initialized with {len(self.tool_manager._tools)} tools"
        )

    def get_capabilities(self) -> list[AgentCapability]:
        """Return tool execution capabilities."""
        return [
            AgentCapability(
                name="tool_detection",
                description="Detect when user query requires tool execution",
                input_topics=["user.query"],
                output_topics=["tool.result", "tool.not_found"],
            )
        ]

    async def process_message(self, message: Message) -> None:
        """
        Process user query and execute tool if detected.

        Args:
            message: Message containing user query
        """
        if message.topic != "user.query":
            return

        # Validate payload
        try:
            payload = validate_message_payload(message.payload, UserQueryPayload, self.agent_id)
        except AgentMessageError as exc:
            self.logger.error("Invalid user query: %s", exc)
            await self.publish(
                topic="tool.not_found",
                payload={"query": "", "error": str(exc)},
                correlation_id=message.correlation_id,
            )
            return
        
        # Use validated data
        query = payload.text

        # Try to detect and execute tool
        tool_result = await self._detect_and_execute_tool(query)

        if tool_result:
            # Tool was executed
            await self.publish(
                topic="tool.result",
                payload={
                    "query": query,
                    "tool_name": tool_result["tool_name"],
                    "success": tool_result["success"],
                    "output": tool_result["output"],
                    "error": tool_result.get("error"),
                },
                priority=MessagePriority.HIGH,
                correlation_id=message.correlation_id,
            )
        else:
            # No tool detected - let dialog agent handle it
            await self.publish(
                topic="tool.not_found",
                payload={"query": query},
                priority=MessagePriority.NORMAL,
                correlation_id=message.correlation_id,
            )

    async def _detect_and_execute_tool(self, query: str) -> Optional[dict]:
        """
        Detect if query requires tool and execute it.

        Args:
            query: User query text

        Returns:
            Tool result dict if tool was executed, None otherwise
        """
        # Check time query
        if self._tool_patterns["time"].search(query):
            return await self._execute_time_tool(query)

        # Check date query
        if self._tool_patterns["date"].search(query):
            return await self._execute_date_tool()

        # Check calculation
        if self._tool_patterns["calculate"].search(query):
            return await self._execute_calculator_tool(query)

        # Check file operations
        if self._tool_patterns["files"].search(query):
            return await self._execute_list_files_tool(query)

        if self._tool_patterns["read_file"].search(query):
            return await self._execute_read_file_tool(query)

        if self._tool_patterns["write_file"].search(query):
            return await self._execute_write_file_tool(query)

        # Check system info
        if self._tool_patterns["system"].search(query):
            return await self._execute_system_info_tool()

        # Check performance monitor
        if self._tool_patterns["performance"].search(query):
            return await self._execute_performance_tool()

        # Check web search
        if self._tool_patterns["web_search"].search(query):
            return await self._execute_web_search_tool(query)

        return None

    async def _execute_time_tool(self, query: str) -> dict:
        """Execute time tool with timezone extraction."""
        timezone = None
        tz_match = re.search(r"\bin\s+(\w+(?:\s+\w+)?)\b", query, re.IGNORECASE)
        if tz_match:
            timezone = tz_match.group(1)

        result = self.tool_manager.execute_tool("get_current_time", timezone=timezone)
        return {
            "tool_name": "get_current_time",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_date_tool(self) -> dict:
        """Execute date tool."""
        result = self.tool_manager.execute_tool("get_current_date")
        return {
            "tool_name": "get_current_date",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_calculator_tool(self, query: str) -> dict:
        """Execute calculator tool by extracting expression."""
        # Extract mathematical expression
        expr_match = re.search(
            r"(?:calculate|compute|what\s+is|how\s+much\s+is)\s+(.+?)(?:\?|$)",
            query,
            re.IGNORECASE,
        )
        if not expr_match:
            # Try to find expression after common words
            expr_match = re.search(r"(\d+[\s\+\-\*\/\(\)]+.*)", query)

        expression = expr_match.group(1).strip() if expr_match else query

        result = self.tool_manager.execute_tool("calculator", expression=expression)
        return {
            "tool_name": "calculator",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_list_files_tool(self, query: str) -> dict:
        """Execute list files tool with path extraction."""
        # Try to extract path from query
        path_match = re.search(r"in\s+['\"]?([^\s'\"]+)", query, re.IGNORECASE)
        directory = path_match.group(1) if path_match else "."

        result = self.tool_manager.execute_tool("list_files", directory=directory)
        return {
            "tool_name": "list_files",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_read_file_tool(self, query: str) -> dict:
        """Execute read file tool with path extraction."""
        # Extract file path
        path_match = re.search(r"['\"]([^'\"]+)['\"]", query)
        if not path_match:
            path_match = re.search(r"file\s+([^\s]+)", query, re.IGNORECASE)

        if not path_match:
            return {
                "tool_name": "read_file",
                "success": False,
                "output": "",
                "error": "Could not extract file path from query",
            }

        filepath = path_match.group(1)
        result = self.tool_manager.execute_tool("read_file", filepath=filepath)
        return {
            "tool_name": "read_file",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_write_file_tool(self, query: str) -> dict:
        """Execute write file tool with path and content extraction."""
        # This is complex - for now return error asking for more info
        return {
            "tool_name": "write_file",
            "success": False,
            "output": "",
            "error": "Write file requires explicit filepath and content parameters",
        }

    async def _execute_system_info_tool(self) -> dict:
        """Execute system info tool."""
        result = self.tool_manager.execute_tool("system_info")
        return {
            "tool_name": "system_info",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_performance_tool(self) -> dict:
        """Execute performance monitor tool."""
        result = self.tool_manager.execute_tool("performance_monitor")
        return {
            "tool_name": "performance_monitor",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }

    async def _execute_web_search_tool(self, query: str) -> dict:
        """Execute web search tool."""
        # Extract search query (remove trigger words)
        search_query = re.sub(
            r"\b(search\s+(the\s+)?web|google|look\s+up|find\s+online)\s+(for\s+)?",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip()

        result = self.tool_manager.execute_tool("web_search", query=search_query)
        return {
            "tool_name": "web_search",
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }
