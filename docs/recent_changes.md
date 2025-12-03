# Recent Changes (MCP Integration)

This branch now includes the first end-to-end MCP wiring for Freya:

- **MCP client and tool discovery/routing.** `FreyaMCPClient` manages server lifecycles, discovers tools over JSON-over-stdio, and issues tool calls through a minimal protocol placeholder. 【F:freya_mcp/client.py†L42-L194】
- **System MCP server tools.** The system server now exposes echo, tool listing, app launching, and directory listing handlers, making OS control available via MCP. 【F:freya_mcp/servers/freya_system_server/server.py†L18-L200】
- **Audio MCP server tools.** The audio server provides transcription and ElevenLabs TTS alongside tool discovery, with lazy initialization of STT/TTS stacks and structured error handling. 【F:freya_mcp/servers/freya_audio_server/server.py†L19-L283】
- **MCP-enabled orchestrator and wake loop entrypoint.** The orchestrator now negotiates tool schemas with the LLM, dispatches MCP tool calls, and optionally speaks replies; `start_freya_mcp.py` wires wake-word capture to this loop and starts MCP servers. 【F:freya/coordination/orchestrator_mcp.py†L1-L165】【F:freya/start_freya_mcp.py†L1-L142】
- **Packaging updates for all subpackages.** `pyproject.toml` now auto-discovers every `freya*` and `freya_mcp*` subpackage to ensure MCP modules install correctly. 【F:pyproject.toml†L104-L107】
