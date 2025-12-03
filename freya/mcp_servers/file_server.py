"""
File Operations MCP Server for Freya

This server provides file operation tools with path traversal protection
using the official MCP Python SDK.
"""

import mimetypes
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

# Create server instance
server = Server("freya-file-server")

# File size limits (in bytes)
MAX_READ_SIZE = 1024 * 1024  # 1 MB
MAX_WRITE_SIZE = 10 * 1024 * 1024  # 10 MB

# Allowed MIME types for reading
ALLOWED_MIME_TYPES = {
    "text/plain", "text/html", "text/css", "text/javascript",
    "text/csv", "text/markdown", "text/xml",
    "application/json", "application/xml", "application/javascript",
    "application/x-yaml", "application/yaml",
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".xml", ".html", ".htm", ".css", ".csv", ".log", ".ini", ".cfg", ".conf",
}

# Magic bytes for binary formats to reject
BINARY_MAGIC_BYTES = {
    b"\x89PNG": "PNG image",
    b"\xFF\xD8\xFF": "JPEG image",
    b"GIF87a": "GIF image",
    b"GIF89a": "GIF image",
    b"%PDF": "PDF document",
    b"PK\x03\x04": "ZIP archive",
    b"PK\x05\x06": "ZIP archive",
    b"MZ": "Windows executable",
    b"\x7FELF": "Linux executable",
    b"\xCA\xFE\xBA\xBE": "Mac executable",
}

# Allowed base directories
ALLOWED_DIRECTORIES = [
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.cwd() / "data",
    Path.cwd() / "logs",
]


def validate_path(file_path: str) -> tuple[Optional[Path], Optional[str]]:
    """Validate file path is within allowed directories."""
    try:
        requested_path = Path(file_path).expanduser().resolve()

        for allowed_dir in ALLOWED_DIRECTORIES:
            try:
                allowed_dir = allowed_dir.resolve()
                requested_path.relative_to(allowed_dir)
                return requested_path, None
            except ValueError:
                continue

        allowed_str = "\n  ".join(str(d) for d in ALLOWED_DIRECTORIES)
        return None, (
            f"Access denied: {file_path} is outside allowed directories.\n"
            f"Allowed directories:\n  {allowed_str}"
        )

    except Exception as e:
        return None, f"Invalid path: {e}"


def validate_file_size(file_path: Path, max_size: int, operation: str) -> Optional[str]:
    """Validate file size is within limits."""
    try:
        file_size = file_path.stat().st_size
        if file_size > max_size:
            size_mb = file_size / (1024 * 1024)
            limit_mb = max_size / (1024 * 1024)
            return (
                f"File too large to {operation}: {size_mb:.2f} MB exceeds "
                f"{limit_mb:.2f} MB limit"
            )
        return None
    except Exception as e:
        return f"Failed to check file size: {e}"


def validate_file_type(file_path: Path) -> tuple[Optional[str], Optional[str]]:
    """Validate file type is text-based and safe to read."""
    try:
        # Check magic bytes first
        with open(file_path, "rb") as f:
            header = f.read(16)

        for magic_bytes, file_type in BINARY_MAGIC_BYTES.items():
            if header.startswith(magic_bytes):
                return None, f"Cannot read binary file: {file_type} detected"

        # Try MIME type detection
        mime_type, _ = mimetypes.guess_type(str(file_path))

        if mime_type and mime_type in ALLOWED_MIME_TYPES:
            return mime_type, None

        # Fallback to extension checking
        extension = file_path.suffix.lower()
        if extension in ALLOWED_EXTENSIONS:
            return mime_type or f"text/plain (extension: {extension})", None

        # Reject unknown types
        if mime_type:
            return None, (
                f"File type not allowed: {mime_type}\n"
                f"Only text-based files are supported"
            )
        else:
            return None, (
                f"Unknown file type with extension {extension or '(none)'}\n"
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

    except Exception as e:
        return None, f"Failed to validate file type: {e}"


# ============================================================================
# Tool Definitions
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="list_files",
            description="List files and folders in a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list",
                        "default": "."
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match (e.g., '*.txt')",
                        "default": "*"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List files recursively",
                        "default": False
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Show hidden files",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="read_file",
            description="Read the contents of a text file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum number of lines to read",
                        "default": 100
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="write_file",
            description="Write content to a text file (creates or overwrites)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    },
                    "append": {
                        "type": "boolean",
                        "description": "Append to file instead of overwriting",
                        "default": False
                    }
                },
                "required": ["path", "content"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution."""
    if name == "list_files":
        return await _list_files(
            arguments.get("path", "."),
            arguments.get("pattern", "*"),
            arguments.get("recursive", False),
            arguments.get("show_hidden", False)
        )
    elif name == "read_file":
        return await _read_file(
            arguments["path"],
            arguments.get("max_lines", 100)
        )
    elif name == "write_file":
        return await _write_file(
            arguments["path"],
            arguments["content"],
            arguments.get("append", False)
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# ============================================================================
# Tool Implementations
# ============================================================================

def _format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


async def _list_files(
    path: str = ".",
    pattern: str = "*",
    recursive: bool = False,
    show_hidden: bool = False
) -> list[TextContent]:
    """List files in a directory."""
    try:
        # Validate path security
        base_path, error = validate_path(path)
        if error:
            return [TextContent(type="text", text=f"Error: {error}")]

        if not base_path.exists():
            return [TextContent(type="text", text=f"Error: Path does not exist: {path}")]

        if not base_path.is_dir():
            return [TextContent(type="text", text=f"Error: Not a directory: {path}")]

        # Collect files
        files = []
        dirs = []

        if recursive:
            items = base_path.rglob(pattern)
        else:
            items = base_path.glob(pattern)

        for item in sorted(items):
            if not show_hidden and item.name.startswith("."):
                continue

            relative = item.relative_to(base_path)

            if item.is_dir():
                dirs.append(f"📁 {relative}/")
            else:
                size = item.stat().st_size
                size_str = _format_size(size)
                files.append(f"📄 {relative} ({size_str})")

        # Format output
        output_lines = []
        if dirs:
            output_lines.append("Directories:")
            output_lines.extend(dirs)
        if files:
            if dirs:
                output_lines.append("")
            output_lines.append("Files:")
            output_lines.extend(files)

        if not output_lines:
            output_lines = [f"No files matching '{pattern}' in {base_path}"]

        output = "\n".join(output_lines)
        return [TextContent(type="text", text=output)]

    except PermissionError:
        return [TextContent(type="text", text=f"Error: Permission denied: {path}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: Failed to list files: {e}")]


async def _read_file(path: str, max_lines: int = 100) -> list[TextContent]:
    """Read a text file."""
    try:
        # Validate path security
        file_path, error = validate_path(path)
        if error:
            return [TextContent(type="text", text=f"Error: {error}")]

        if not file_path.exists():
            return [TextContent(type="text", text=f"Error: File does not exist: {path}")]

        if not file_path.is_file():
            return [TextContent(type="text", text=f"Error: Not a file: {path}")]

        # Validate file type
        mime_type, type_error = validate_file_type(file_path)
        if type_error:
            return [TextContent(type="text", text=f"Error: {type_error}")]

        # Validate file size
        size_error = validate_file_size(file_path, MAX_READ_SIZE, "read")
        if size_error:
            return [TextContent(type="text", text=f"Error: {size_error}")]

        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... (truncated at {max_lines} lines)")
                    break
                lines.append(line.rstrip())

        output = "\n".join(lines)
        return [TextContent(type="text", text=output)]

    except UnicodeDecodeError:
        return [TextContent(type="text", text=f"Error: Cannot read binary file: {path}")]
    except PermissionError:
        return [TextContent(type="text", text=f"Error: Permission denied: {path}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: Failed to read file: {e}")]


async def _write_file(path: str, content: str, append: bool = False) -> list[TextContent]:
    """Write to a file."""
    try:
        # Validate content size
        content_size = len(content.encode("utf-8"))
        content_size_mb = content_size / (1024 * 1024)
        limit_mb = MAX_WRITE_SIZE / (1024 * 1024)

        if content_size > MAX_WRITE_SIZE:
            return [TextContent(
                type="text",
                text=f"Error: Content too large: {content_size_mb:.2f} MB exceeds {limit_mb:.2f} MB limit"
            )]

        # Validate path security
        file_path, error = validate_path(path)
        if error:
            return [TextContent(type="text", text=f"Error: {error}")]

        # For append mode, check final size
        if append and file_path.exists():
            current_size = file_path.stat().st_size
            final_size = current_size + content_size
            if final_size > MAX_WRITE_SIZE:
                current_mb = current_size / (1024 * 1024)
                final_mb = final_size / (1024 * 1024)
                return [TextContent(
                    type="text",
                    text=f"Error: Append would exceed limit: {current_mb:.2f} MB + {content_size_mb:.2f} MB = {final_mb:.2f} MB"
                )]

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        mode = "a" if append else "w"
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)

        action = "Appended to" if append else "Wrote"
        size = file_path.stat().st_size

        return [TextContent(
            type="text",
            text=f"{action} {len(content)} characters to {file_path} (total size: {size} bytes)"
        )]

    except PermissionError:
        return [TextContent(type="text", text=f"Error: Permission denied: {path}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: Failed to write file: {e}")]


# ============================================================================
# Server Entry Point
# ============================================================================

async def main():
    """Run the server using stdio transport."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
