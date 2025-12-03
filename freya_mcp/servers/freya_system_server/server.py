"""Minimal MCP server exposing stub system tools.

Phase 1 keeps transport intentionally simple: JSON messages over stdin/stdout,
one message per line. This skeleton echoes requests so client wiring can be
tested without invoking real system commands yet.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    args_schema: Dict[str, Any] | None = None


TOOLS: List[MCPTool] = [
    MCPTool(
        name="freya.system.echo",
        description="Echo text back to the caller for protocol validation.",
        args_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    ),
    MCPTool(
        name="freya.system.list_tools",
        description="Return metadata for all tools exposed by this MCP server.",
        args_schema={"type": "object", "properties": {}},
    ),
    MCPTool(
        name="freya.system.open_application",
        description="Open a desktop application by providing its full path.",
        args_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
    MCPTool(
        name="freya.system.list_directory",
        description="List files and folders in a given directory.",
        args_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
]


def list_tools_handler(_: Dict[str, Any]) -> Dict[str, Any]:
    """Return metadata for all tools exposed by this MCP server."""

    return {
        "type": "tool_result",
        "tool": "freya.system.list_tools",
        "success": True,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema,
            }
            for tool in TOOLS
        ],
    }


def echo_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Echo text back to the caller for protocol validation."""

    message = args.get("message", "")
    return {"type": "tool_result", "tool": "freya.system.echo", "success": True, "output": message}


def open_application_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Open a desktop application by launching the provided path."""

    path = args.get("path")
    if not path:
        return {
            "type": "tool_result",
            "tool": "freya.system.open_application",
            "success": False,
            "error": "Argument 'path' is required",
        }

    try:
        subprocess.Popen([path])
        return {"type": "tool_result", "tool": "freya.system.open_application", "success": True}
    except Exception as exc:  # pragma: no cover - best-effort logging for now
        return {
            "type": "tool_result",
            "tool": "freya.system.open_application",
            "success": False,
            "error": str(exc),
        }


def list_directory_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """List files and folders in a given directory."""

    path = args.get("path")
    if not path:
        return {
            "type": "tool_result",
            "tool": "freya.system.list_directory",
            "success": False,
            "error": "Argument 'path' is required",
        }

    try:
        items = os.listdir(path)
        return {
            "type": "tool_result",
            "tool": "freya.system.list_directory",
            "success": True,
            "items": items,
        }
    except Exception as exc:  # pragma: no cover - best-effort logging for now
        return {
            "type": "tool_result",
            "tool": "freya.system.list_directory",
            "success": False,
            "error": str(exc),
        }


TOOL_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "freya.system.echo": echo_handler,
    "freya.system.list_tools": list_tools_handler,
    "freya.system.open_application": open_application_handler,
    "freya.system.list_directory": list_directory_handler,
}


def iter_requests(stream: Iterable[str]) -> Iterable[Dict[str, Any]]:
    """Yield decoded JSON requests from an input stream."""

    for line in stream:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            yield {"type": "error", "error": "Invalid JSON"}


def serialize_response(response: Dict[str, Any]) -> str:
    """Serialize responses as single-line JSON for stdout."""

    return json.dumps(response, ensure_ascii=False)


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a single MCP request.

    Supported messages (phase 1):
    - {"type": "list_tools"}
    - {"type": "call_tool", "tool": "freya.system.echo", "args": {"message": "..."}}
    """

    if request.get("type") == "list_tools":
        return {
            "type": "tool_list",
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": tool.args_schema,
                }
                for tool in TOOLS
            ],
        }

    if request.get("type") == "call_tool":
        tool_name = request.get("tool")
        args = request.get("args") or {}

        handler = TOOL_HANDLERS.get(tool_name)
        if handler:
            return handler(args)

        return {
            "type": "tool_result",
            "tool": tool_name,
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    return {"type": "error", "error": "Unsupported request"}


def main() -> None:
    """Run the request loop."""

    for request in iter_requests(sys.stdin):
        response = handle_request(request)
        sys.stdout.write(serialize_response(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

