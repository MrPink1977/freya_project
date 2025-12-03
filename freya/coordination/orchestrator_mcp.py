"""Minimal MCP-aware orchestrator loop.

This orchestrator focuses on the agent-tool handshake for MCP-enabled tools:
- ask the LLM for the next action including tool metadata
- detect tool calls in the LLM response
- route tool calls through the MCP client
- feed tool results back to the LLM for a final reply
- optionally speak the final reply via MCP TTS
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from freya.core.context import ConversationContext
from freya.core.ollama_client import OllamaClient
from freya_mcp.client import FreyaMCPClient


class MCPOrchestrator:
    """Run a single round of LLM ↔ MCP tool interaction."""

    def __init__(
        self,
        llm_client: OllamaClient,
        mcp_client: FreyaMCPClient,
        context: ConversationContext,
        *,
        auto_speak: bool = True,
        speak_tool: str = "freya.audio.speak_el",
    ) -> None:
        self._llm_client = llm_client
        self._mcp_client = mcp_client
        self._context = context
        self._auto_speak = auto_speak
        self._speak_tool = speak_tool

    def warm_up_tools(self) -> None:
        """Start MCP servers (if configured) and refresh tool metadata."""

        self._mcp_client.start_servers()
        self._mcp_client.discover_tools()

    def _tool_schemas(self) -> List[Dict]:
        """Convert MCP tool registrations into LLM-friendly schema objects."""

        schemas: List[Dict] = []
        for tool in self._mcp_client.list_tools():
            schema = {
                "name": tool.name,
                "description": tool.description,
            }
            if tool.args_schema:
                schema["parameters"] = tool.args_schema
            schemas.append(schema)
        return schemas

    def _extract_tool_call(self, llm_message: Dict) -> Optional[Dict]:
        """Return the first tool call from an Ollama-style response message."""

        if not llm_message:
            return None

        tool_calls = llm_message.get("tool_calls") or []
        if not tool_calls:
            return None

        return tool_calls[0]

    def _call_mcp_tool(self, tool_name: str, args: Dict) -> Dict:
        """Invoke a tool through the MCP client and wrap the response."""

        result = self._mcp_client.call_tool(tool_name, args)
        return {
            "role": "tool",
            "name": tool_name,
            "content": json.dumps(result, ensure_ascii=False),
        }

    def _speak_if_configured(self, text: str) -> None:
        if not self._auto_speak or not text.strip():
            return

        try:
            self._mcp_client.call_tool(self._speak_tool, {"text": text})
        except Exception:
            # Speech is best-effort; failures should not break the loop.
            return

    def handle_audio_input(self, audio_path: str) -> str:
        """Transcribe audio via MCP, then run a full reasoning round.

        This keeps the wake-word pipeline thin: once a recording is captured
        (e.g. after detecting the wake word), it is passed here for
        transcription and follow-up orchestration.
        """

        try:
            transcription = self._mcp_client.call_tool(
                "freya.audio.transcribe", {"file_path": str(audio_path)}
            )
        except Exception as exc:
            error = f"Transcription failed: {exc}"
            self._context.add_assistant_message(error)
            return error

        if not isinstance(transcription, dict) or not transcription.get("success"):
            error = transcription.get("error") if isinstance(transcription, dict) else None
            message = error or "Transcription failed"
            self._context.add_assistant_message(message)
            return message

        transcript = str(transcription.get("text", "")).strip()
        if not transcript:
            message = "[No speech detected]"
            self._context.add_assistant_message(message)
            return message

        return self.run_mcp_round(transcript)

    def run_mcp_round(self, user_text: str) -> str:
        """Execute a single MCP-enabled reasoning round."""

        # Update context with the latest user turn.
        self._context.add_user_message(user_text)

        # Ask the LLM what to do, including available tools.
        messages = self._context.as_messages()
        tools_schema = self._tool_schemas()
        initial = self._llm_client.chat_with_tools(messages, tools_schema)

        message_dict = initial.get("message") if isinstance(initial, dict) else {}
        content = initial.get("content", "") if isinstance(initial, dict) else str(initial)

        tool_call = self._extract_tool_call(message_dict if isinstance(message_dict, dict) else {})
        if tool_call:
            function = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
            tool_name = function.get("name") if isinstance(function, dict) else None
            raw_args = function.get("arguments") if isinstance(function, dict) else None
            try:
                parsed_args = {} if raw_args is None else json.loads(raw_args)
            except Exception:
                parsed_args = {}

            if tool_name:
                tool_message = self._call_mcp_tool(tool_name, parsed_args)
                # Store the LLM request and tool result for grounding the follow-up call.
                self._context.add_assistant_message(content or f"[Tool call] {tool_name}")
                self._context.add_assistant_message(tool_message.get("content", ""))

                follow_up_messages = self._context.as_messages()
                follow_up_messages.append(tool_message)
                final_response = self._llm_client.chat(follow_up_messages)
                self._context.add_assistant_message(final_response)
                self._speak_if_configured(final_response)
                return final_response

        # No tool invocation required—treat the LLM content as the reply.
        self._context.add_assistant_message(content)
        self._speak_if_configured(content)
        return content


__all__ = ["MCPOrchestrator"]
