"""File operation tools for Freya with path traversal protection."""

from __future__ import annotations

import os
import mimetypes
from pathlib import Path
from typing import Optional

from .base import FreyaTool, ToolResult


# File size limits (in bytes)
MAX_READ_SIZE = 1024 * 1024  # 1 MB - max file size to read
MAX_WRITE_SIZE = 10 * 1024 * 1024  # 10 MB - max content size to write


# Allowed MIME types for reading
ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/html",
    "text/css",
    "text/javascript",
    "text/csv",
    "text/markdown",
    "text/xml",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-yaml",
    "application/yaml",
}

# Allowed file extensions (fallback when MIME detection fails)
ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".csv",
    ".log",
    ".ini",
    ".cfg",
    ".conf",
}

# Magic bytes for common binary formats to reject
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


def validate_file_size(file_path: Path, max_size: int, operation: str) -> Optional[str]:
    """
    Validate file size is within limits.

    Args:
        file_path: Path to file to check
        max_size: Maximum allowed size in bytes
        operation: Operation name for error message ('read' or 'write')

    Returns:
        Error message if validation fails, None otherwise
    """
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
    """
    Validate file type is text-based and safe to read.

    Uses MIME type detection, extension checking, and magic byte detection
    to determine if a file is safe to read as text.

    Args:
        file_path: Path to file to validate

    Returns:
        Tuple of (mime_type, error_message). If error_message is not None, file is unsafe.
    """
    try:
        # Check magic bytes first (fast rejection of binary files)
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
                f"Only text-based files are supported (text/*, application/json, etc.)"
            )
        else:
            return None, (
                f"Unknown file type with extension {extension or '(none)'}\n"
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
    
    except Exception as e:
        return None, f"Failed to validate file type: {e}"


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

            # Validate file type
            mime_type, type_error = validate_file_type(file_path)
            if type_error:
                return ToolResult(success=False, output="", error=type_error)

            # Validate file size
            size_error = validate_file_size(file_path, MAX_READ_SIZE, "read")
            if size_error:
                return ToolResult(success=False, output="", error=size_error)

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
                    "mime_type": mime_type,
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
            # Validate content size
            content_size = len(content.encode("utf-8"))
            content_size_mb = content_size / (1024 * 1024)
            limit_mb = MAX_WRITE_SIZE / (1024 * 1024)
            
            if content_size > MAX_WRITE_SIZE:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Content too large to write: {content_size_mb:.2f} MB exceeds {limit_mb:.2f} MB limit",
                )

            # Validate path security
            file_path, error = validate_path(path)
            if error:
                return ToolResult(success=False, output="", error=error)

            # For append mode, check final size won't exceed limit
            if append and file_path.exists():
                current_size = file_path.stat().st_size
                final_size = current_size + content_size
                if final_size > MAX_WRITE_SIZE:
                    current_mb = current_size / (1024 * 1024)
                    final_mb = final_size / (1024 * 1024)
                    return ToolResult(
                        success=False,
                        output="",
                        error=(
                            f"Append would exceed size limit: current {current_mb:.2f} MB + "
                            f"new {content_size_mb:.2f} MB = {final_mb:.2f} MB > {limit_mb:.2f} MB limit"
                        ),
                    )

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
