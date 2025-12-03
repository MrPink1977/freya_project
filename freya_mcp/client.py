"""Minimal MCP client for managing tool servers.

This skeleton focuses on process lifecycle and a placeholder interface that can
be expanded as the MCP protocol is fleshed out. It intentionally avoids
coupling to the current ToolManager so we can evolve the transport separately.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for launching an MCP server process."""

    name: str
    command: List[str]
    cwd: Optional[Path] = None
    env: Optional[Dict[str, str]] = None
    # Future: add health checks, restart policies, logging destinations


@dataclass
class ToolRegistration:
    """Metadata describing a tool provided by an MCP server."""

    name: str
    description: str
    server_name: str
    args_schema: Dict | None = field(default=None)


class FreyaMCPClient:
    """Manage MCP server processes and route tool calls.

    Phase 1 keeps the interface minimal and focused on lifecycle management.
    Tool routing and protocol handling will be layered on in subsequent phases.
    """

    def __init__(self, server_configs: Iterable[MCPServerConfig] | None = None) -> None:
        self._server_configs: Dict[str, MCPServerConfig] = {
            config.name: config for config in (server_configs or [])
        }
        self._processes: Dict[str, subprocess.Popen] = {}
        self._tools: Dict[str, ToolRegistration] = {}

    def register_server(self, config: MCPServerConfig) -> None:
        """Add a server configuration to the client without launching it."""

        self._server_configs[config.name] = config

    def start_servers(self) -> None:
        """Launch all configured MCP servers.

        Servers are started with text-mode stdio streams so the eventual
        JSON-over-stdio protocol can be layered on without relaunching.
        """

        for name, config in self._server_configs.items():
            if name in self._processes and self._processes[name].poll() is None:
                continue

            process = subprocess.Popen(
                config.command,
                cwd=str(config.cwd) if config.cwd else None,
                env=config.env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._processes[name] = process

    def stop_servers(self, timeout: float = 2.0) -> None:
        """Terminate all running MCP servers."""

        for name, process in list(self._processes.items()):
            if process.poll() is not None:
                self._processes.pop(name, None)
                continue

            process.terminate()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
            finally:
                self._processes.pop(name, None)

    def list_tools(self) -> List[ToolRegistration]:
        """Return the currently known tools.

        Phase 1 returns whatever has been manually registered or discovered via
        future handshake messages. Until the MCP protocol is wired, this will be
        empty.
        """

        return sorted(self._tools.values(), key=lambda tool: tool.name)

    def register_tool(self, tool: ToolRegistration) -> None:
        """Register a tool that a server exposes.

        This keeps the client interface usable for the orchestrator even before
        full discovery/handshake flows exist.
        """

        self._tools[tool.name] = tool

    def discover_tools(self) -> None:
        """Query all servers for their advertised tools.

        Each server is asked for a ``list_tools`` response and any tools are
        registered locally for routing. Discovery is best-effort: individual
        server errors are logged and skipped so that other servers can still be
        registered.
        """

        for server_name in self._server_configs:
            try:
                response = self._send_request(server_name, {"type": "list_tools"})
            except Exception as exc:  # pragma: no cover - defensive best-effort
                logger.warning("Tool discovery failed for server '%s': %s", server_name, exc)
                continue

            tools = response.get("tools") if isinstance(response, dict) else None
            if not tools:
                logger.debug(
                    "Server '%s' returned no tools during discovery: %s", server_name, response
                )
                continue

            for tool in tools:
                name = tool.get("name")
                description = tool.get("description", "")
                args_schema = tool.get("args_schema") if isinstance(tool, dict) else None
                if not name:
                    continue
                self.register_tool(
                    ToolRegistration(
                        name=name,
                        description=description,
                        server_name=server_name,
                        args_schema=args_schema,
                    )
                )

    def call_tool(self, tool_name: str, args: Optional[Dict] = None) -> Dict:
        """Invoke a tool via its MCP server.

        The wire protocol is intentionally deferred to later phases. This
        placeholder raises to make the current limitation explicit to callers.
        """

        registration = self._tools.get(tool_name)
        if registration is None:
            raise KeyError(f"Tool not registered: {tool_name}")

        server_name = registration.server_name
        request = {"type": "call_tool", "tool": tool_name, "args": args or {}}
        return self._send_request(server_name, request)

    def _send_request(self, server_name: str, payload: Dict) -> Dict:
        """Send a single JSON request to a server and return the decoded reply."""

        process = self._processes.get(server_name)
        if process is None or process.poll() is not None:
            raise RuntimeError(f"Server '{server_name}' is not running")
        if process.stdin is None or process.stdout is None:
            raise RuntimeError(f"Server '{server_name}' stdio is unavailable")

        encoded = json.dumps(payload, ensure_ascii=False)
        process.stdin.write(encoded + "\n")
        process.stdin.flush()

        line = process.stdout.readline()
        if not line:
            raise RuntimeError(f"No response received from server '{server_name}'")

        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Invalid JSON response from server '{server_name}': {line!r}"
            ) from exc

    def __enter__(self) -> "FreyaMCPClient":
        self.start_servers()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop_servers()

