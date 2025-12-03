# MCP Migration Plan

## Goals
- Replace intent-style tool routing with MCP-style tool calls while keeping Freya usable during the transition.
- Introduce a stable client/server contract so tools can be added, versioned, and sandboxed independently.
- Minimize blast radius by enabling feature-flagged rollout and side-by-side execution with the current tool path.

## Scope and initial assumptions
- Start with JSON-over-stdio MCP servers; evolve protocol (schemas, streaming, auth) later.
- Reuse existing tool implementations (STT, TTS, vision, automation, system) and `ToolManager` where practical to keep behavior unchanged.
- Target Windows + local dev parity; scripts will mirror the `scripts/start_*.bat` patterns already used.

## Milestones (incremental, shippable states)
1. **Foundation (skeleton only)**
   - Add `freya_mcp/client.py` stub with process lifecycle management (start/stop servers, registry, simple `call_tool`).
   - Add a single `freya_mcp/servers/freya_system_server/server.py` with a no-op handler to validate JSON-over-stdio loop and message framing.
   - Update the orchestrator prompt to advertise an empty tool list sourced from the MCP client (ensures wiring compiles without real tools).

2. **First real tool (system.run_command)**
   - Implement `freya.system.run_command` in the system MCP server, delegating to existing command execution utilities with timeouts.
   - Wire `FreyaMCPClient.call_tool` to route requests to the system server; shape responses to match current tool result objects.
   - Add a feature flag/env var to choose MCP vs. direct `ToolManager` for this tool; default to MCP in dev.
   - Smoke test via a simple conversation: “list files” → MCP call → orchestrator receives result.

3. **Expand tool surface area**
   - **Audio server**: wrap `freya.audio.transcribe` (Whisper) and `freya.audio.speak` (Piper) with basic argument validation.
   - **Vision server**: wrap `freya.vision.capture_frame` and any analysis helpers (e.g., trichome detection) as separate tools.
   - **Automation server**: wrap the deer deterrent/other actuations behind concise tool names with clear arg schemas.
   - Add tool metadata (name, description, args schema) to the MCP registry and propagate to the orchestrator’s LLM prompt.
   - Keep old paths behind a feature flag for rollback; prefer MCP for day-to-day use once stable.

4. **Orchestrator simplification**
   - Remove legacy intent parsing and direct `ToolManager` calls once MCP paths cover required tools.
   - Normalize tool result shapes to avoid downstream conditionals.
   - Add structured logging around MCP calls (request/response IDs, timing, stderr) for debuggability.

5. **Robustness + ops**
   - Add health checks and supervised process management (auto-restart on crash, stop clean-up on shutdown).
   - Introduce schema validation for tool args/results (pydantic/dataclasses) to catch bad payloads early.
   - Add startup scripts (Windows + POSIX) to launch all MCP servers plus Freya orchestrator together; consider Windows services later.
   - Write regression tests for MCP client/server round-trips and representative tool calls.

## Work breakdown (who does what, roughly)
- **MCP client/registry**: implement lifecycle + routing; add logging and error handling.
- **Servers**: one owner per domain (system, audio, vision, automation); each wraps existing functions, keeping signatures stable.
- **Orchestrator/LLM prompt**: expose MCP tool metadata to the model; handle MCP tool call responses uniformly.
- **DevOps**: scripts/services for auto-start, plus monitoring/logging hooks.

## Risks and mitigations
- **Protocol drift**: start with minimal JSON; gate changes behind versioned message fields and keep legacy path available until parity is proven.
- **Process stability**: supervise servers (timeouts, retries, exit codes); add integration tests that simulate crashes.
- **Argument mismatch**: reuse existing validation; document tool schemas in one place (registry) to keep prompt and server aligned.
- **Audio/vision streaming complexity**: begin with non-streaming commands; plan a later protocol revision for streaming if needed.

## Definition of done for phase 1–2
- MCP client can start/stop the system server and list available tools.
- `freya.system.run_command` works end-to-end via MCP with parity to the current implementation.
- Orchestrator prompt advertises tools from the MCP registry and can satisfy a basic “list files” request.
- Feature flag exists to fall back to the legacy path without code changes.
