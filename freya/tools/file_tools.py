"""File operation tools for Freya with path traversal protection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .base import FreyaTool, ToolResult


# Define allowed base directories for file operations
ALLOWED_DIRECTORIES = [
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.cwd() / "data",  # Project data directory
    Path.cwd() / "logs",  # Project logs directory
]


def validate_path(file_path: str) -> tuple[Optional[Path], Optional[str]]:
    """
    Validate file path is within allowed directories.

    Args:
        file_path: Path to validate

    Returns:
        Tuple of (resolved_path, error_message). If error_message is not None, path is unsafe.
    """
    try:
        # Convert to absolute path and resolve (follows symlinks, removes ..)
        requested_path = Path(file_path).expanduser().resolve()

        # Check if path is within any allowed directory
        for allowed_dir in ALLOWED_DIRECTORIES:
            try:
                allowed_dir = allowed_dir.resolve()
                # relative_to() raises ValueError if not a subpath
                requested_path.relative_to(allowed_dir)
                return requested_path, None  # Safe!
            except ValueError:
                continue  # Try next allowed directory

        # Not in any allowed directory
        allowed_str = "\n  ".join(str(d) for d in ALLOWED_DIRECTORIES)
        return None, (
            f"Access denied: {file_path} is outside allowed directories.\n"
            f"Allowed directories:\n  {allowed_str}"
        )

    except Exception as e:
        return None, f"Invalid path: {e}"


class ListFilesTool(FreyaTool):
    """List files and directories in a path."""

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files and folders in a directory"

    def execute(
        self,
        path: str = ".",
        pattern: str = "*",
        recursive: bool = False,
        show_hidden: bool = False,
    ) -> ToolResult:
        """List files in a directory.

        Args:
            path: Directory path to list (default: current directory)
            pattern: File pattern to match (e.g., '*.txt', '*.py')
            recursive: List files recursively
            show_hidden: Show hidden files (starting with .)

        Returns:
            ToolResult with file list
        """
        try:
            # Validate path security
            base_path, error = validate_path(path)
            if error:
                return ToolResult(success=False, output="", error=error)

            if not base_path.exists():
                return ToolResult(success=False, output="", error=f"Path does not exist: {path}")

            if not base_path.is_dir():
                return ToolResult(success=False, output="", error=f"Not a directory: {path}")

            # Collect files
            files = []
            dirs = []

            if recursive:
                items = base_path.rglob(pattern)
            else:
                items = base_path.glob(pattern)

            for item in sorted(items):
                # Skip hidden files if requested
                if not show_hidden and item.name.startswith("."):
                    continue

                relative = item.relative_to(base_path)

                if item.is_dir():
                    dirs.append(f"📁 {relative}/")
                else:
                    size = item.stat().st_size
                    size_str = self._format_size(size)
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

            return ToolResult(
                success=True,
                output=output,
                metadata={"path": str(base_path), "file_count": len(files), "dir_count": len(dirs)},
            )

        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to list files: {e}")

    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


class ReadFileTool(FreyaTool):
    """Read contents of a text file."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a text file"

    def execute(self, path: str, max_lines: int = 100) -> ToolResult:
        """Read a text file.

        Args:
            path: File path to read
            max_lines: Maximum number of lines to read (default: 100)

        Returns:
            ToolResult with file contents
        """
        try:
            # Validate path security
            file_path, error = validate_path(path)
            if error:
                return ToolResult(success=False, output="", error=error)

            if not file_path.exists():
                return ToolResult(success=False, output="", error=f"File does not exist: {path}")

            if not file_path.is_file():
                return ToolResult(success=False, output="", error=f"Not a file: {path}")

            # Read file
            with open(file_path, "r", encoding="utf-8") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... (truncated at {max_lines} lines)")
                        break
                    lines.append(line.rstrip())

            output = "\n".join(lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "path": str(file_path),
                    "lines_read": len(lines),
                    "size": file_path.stat().st_size,
                },
            )

        except UnicodeDecodeError:
            return ToolResult(success=False, output="", error=f"Cannot read binary file: {path}")
        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to read file: {e}")


class WriteFileTool(FreyaTool):
    """Write content to a text file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a text file (creates or overwrites)"

    def execute(self, path: str, content: str, append: bool = False) -> ToolResult:
        """Write to a file.

        Args:
            path: File path to write
            content: Content to write
            append: Append to file instead of overwriting

        Returns:
            ToolResult with success status
        """
        try:
            # Validate path security
            file_path, error = validate_path(path)
            if error:
                return ToolResult(success=False, output="", error=error)

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)

            action = "Appended to" if append else "Wrote"
            size = file_path.stat().st_size

            return ToolResult(
                success=True,
                output=f"{action} {len(content)} characters to {file_path} (total size: {size} bytes)",
                metadata={
                    "path": str(file_path),
                    "bytes_written": len(content),
                    "total_size": size,
                    "appended": append,
                },
            )

        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to write file: {e}")


__all__ = ["ListFilesTool", "ReadFileTool", "WriteFileTool"]
