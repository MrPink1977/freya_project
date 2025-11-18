"""System information tools for Freya."""

from __future__ import annotations

import os
import platform
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

    def execute(self, info_type: str = "all") -> ToolResult:  # type: ignore[override]
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
    """Execute safe shell commands."""

    # Whitelist of allowed commands for safety
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
    }

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return "Execute safe shell commands (limited whitelist for security)"

    def execute(self, command: str, timeout: int = 5) -> ToolResult:  # type: ignore[override]
        """Execute a shell command.

        Args:
            command: Command to execute (must be in whitelist)
            timeout: Timeout in seconds (default: 5)

        Returns:
            ToolResult with command output
        """
        try:
            # Parse command
            parts = command.split()
            if not parts:
                return ToolResult(success=False, output="", error="Empty command")

            cmd_name = parts[0]

            # Security check - only allow whitelisted commands
            if cmd_name not in self.ALLOWED_COMMANDS:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command '{cmd_name}' not allowed. Allowed: {', '.join(sorted(self.ALLOWED_COMMANDS))}",
                )

            # Execute command with timeout
            result = subprocess.run(parts, capture_output=True, text=True, timeout=timeout, check=False)

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
