"""System information tools for Freya with command injection protection."""

from __future__ import annotations

import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from datetime import timedelta

from .base import FreyaTool, ToolResult


class SystemInfoTool(FreyaTool):
    """Get system information."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "Get system information (OS, Python version, disk space, etc.)"

    def execute(self, info_type: str = "all") -> ToolResult:
        """Get system information.

        Args:
            info_type: Type of info - 'all', 'os', 'python', 'disk', 'uptime'

        Returns:
            ToolResult with system information
        """
        try:
            info_parts = []

            if info_type in ("all", "os"):
                os_info = (
                    f"OS: {platform.system()} {platform.release()}\n"
                    f"Machine: {platform.machine()}\n"
                    f"Processor: {platform.processor() or 'Unknown'}"
                )
                info_parts.append(os_info)

            if info_type in ("all", "python"):
                py_info = f"Python: {sys.version.split()[0]}\n" f"Executable: {sys.executable}"
                info_parts.append(py_info)

            if info_type in ("all", "disk"):
                try:
                    usage = shutil.disk_usage(os.path.expanduser("~"))
                    total_gb = usage.total / (1024**3)
                    used_gb = usage.used / (1024**3)
                    free_gb = usage.free / (1024**3)
                    percent = (usage.used / usage.total) * 100

                    disk_info = (
                        f"Disk Space:\n"
                        f"  Total: {total_gb:.1f} GB\n"
                        f"  Used: {used_gb:.1f} GB ({percent:.1f}%)\n"
                        f"  Free: {free_gb:.1f} GB"
                    )
                    info_parts.append(disk_info)
                except Exception:
                    info_parts.append("Disk info unavailable")

            if info_type in ("all", "uptime") and platform.system() != "Windows":
                try:
                    with open("/proc/uptime", "r") as f:
                        uptime_seconds = float(f.readline().split()[0])
                        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
                        info_parts.append(f"System Uptime: {uptime_str}")
                except Exception:
                    pass

            output = "\n\n".join(info_parts) if info_parts else "No information available"

            return ToolResult(success=True, output=output)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to get system info: {e}")


class ExecuteCommandTool(FreyaTool):
    """Execute safe shell commands with hybrid security approach."""

    # Whitelist of allowed command names
    ALLOWED_COMMANDS = {
        "ls",
        "dir",
        "pwd",
        "date",
        "whoami",
        "hostname",
        "uptime",
        "df",
        "du",
        "which",
        "echo",
        "cat",
        "head",
        "tail",
        "wc",
        "grep",
        "find",
        "ps",
        "top",
        "netstat",
    }

    # Dangerous patterns that indicate command injection attempts
    DANGEROUS_PATTERNS = [
        r";\s*",  # Command chaining with semicolon
        r"\|\s*",  # Pipe to another command
        r"&&",  # AND command chaining
        r"\|\|",  # OR command chaining
        r"`",  # Command substitution (backticks)
        r"\$\(",  # Command substitution $()
        r">\s*",  # Output redirection
        r"<\s*",  # Input redirection
        r"&\s*$",  # Background execution
    ]

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return "Execute safe shell commands (whitelist + injection protection)"

    def _validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate command for security issues.

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return False, f"Dangerous pattern detected: {pattern}"

        return True, ""

    def execute(self, command: str, timeout: int = 5) -> ToolResult:
        """Execute a shell command safely.

        Args:
            command: Command to execute (must pass security checks)
            timeout: Timeout in seconds (default: 5)

        Returns:
            ToolResult with command output
        """
        try:
            # Security validation
            is_safe, error = self._validate_command(command)
            if not is_safe:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Security check failed: {error}",
                )

            # Parse command using shlex for proper shell-like splitting
            try:
                parts = shlex.split(command)
            except ValueError as e:
                return ToolResult(success=False, output="", error=f"Invalid command syntax: {e}")

            if not parts:
                return ToolResult(success=False, output="", error="Empty command")

            cmd_name = parts[0]

            # Whitelist check
            if cmd_name not in self.ALLOWED_COMMANDS:
                allowed_str = ", ".join(sorted(self.ALLOWED_COMMANDS))
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command '{cmd_name}' not allowed. Allowed: {allowed_str}",
                )

            # Execute with shell=False for security (no shell interpretation)
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,  # Critical: prevents shell injection
            )

            output = result.stdout.strip() if result.stdout else result.stderr.strip()

            if result.returncode != 0 and not output:
                output = f"Command exited with code {result.returncode}"

            return ToolResult(
                success=result.returncode == 0,
                output=output,
                error=result.stderr.strip() if result.returncode != 0 else None,
                metadata={"return_code": result.returncode, "command": command},
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error=f"Command timeout after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output="", error=f"Command not found: {cmd_name}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Execution failed: {e}")


__all__ = ["SystemInfoTool", "ExecuteCommandTool"]
