"""
System MCP Server for Freya

This server provides system information and command execution tools
using the official MCP Python SDK.
"""

import ast
import math
import operator
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from datetime import timedelta
from typing import Union

from mcp.server import Server
from mcp.types import Tool, TextContent

# Create server instance
server = Server("freya-system-server")


# ============================================================================
# System Information Tool
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="system_info",
            description="Get system information (OS, Python version, disk space, uptime)",
            inputSchema={
                "type": "object",
                "properties": {
                    "info_type": {
                        "type": "string",
                        "description": "Type of info to retrieve",
                        "enum": ["all", "os", "python", "disk", "uptime"],
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="execute_command",
            description="Execute safe shell commands (whitelist + injection protection)",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute (must be whitelisted)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 5
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="calculator",
            description="Calculate mathematical expressions (supports +, -, *, /, ^, sqrt, sin, cos, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')"
                    }
                },
                "required": ["expression"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution."""
    if name == "system_info":
        return await _system_info(arguments.get("info_type", "all"))
    elif name == "execute_command":
        return await _execute_command(
            arguments["command"],
            arguments.get("timeout", 5)
        )
    elif name == "calculator":
        return await _calculator(arguments["expression"])
    else:
        raise ValueError(f"Unknown tool: {name}")


# ============================================================================
# System Info Implementation
# ============================================================================

async def _system_info(info_type: str = "all") -> list[TextContent]:
    """Get system information."""
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
            py_info = (
                f"Python: {sys.version.split()[0]}\n"
                f"Executable: {sys.executable}"
            )
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

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: Failed to get system info: {e}")]


# ============================================================================
# Execute Command Implementation
# ============================================================================

# Whitelist of allowed command names
ALLOWED_COMMANDS = {
    "ls", "dir", "pwd", "date", "whoami", "hostname", "uptime",
    "df", "du", "which", "echo", "cat", "head", "tail", "wc",
    "grep", "find", "ps", "top", "netstat",
}

# Dangerous patterns that indicate command injection attempts
DANGEROUS_PATTERNS = [
    r";\s*",      # Command chaining with semicolon
    r"\|\s*",     # Pipe to another command
    r"&&",        # AND command chaining
    r"\|\|",      # OR command chaining
    r"`",         # Command substitution (backticks)
    r"\$\(",      # Command substitution $()
    r">\s*",      # Output redirection
    r"<\s*",      # Input redirection
    r"&\s*$",     # Background execution
]


def _validate_command(command: str) -> tuple[bool, str]:
    """Validate command for security issues."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return False, f"Dangerous pattern detected: {pattern}"
    return True, ""


async def _execute_command(command: str, timeout: int = 5) -> list[TextContent]:
    """Execute a shell command safely."""
    try:
        # Security validation
        is_safe, error = _validate_command(command)
        if not is_safe:
            return [TextContent(type="text", text=f"Error: Security check failed: {error}")]

        # Parse command using shlex
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: Invalid command syntax: {e}")]

        if not parts:
            return [TextContent(type="text", text="Error: Empty command")]

        cmd_name = parts[0]

        # Whitelist check
        if cmd_name not in ALLOWED_COMMANDS:
            allowed_str = ", ".join(sorted(ALLOWED_COMMANDS))
            return [TextContent(
                type="text",
                text=f"Error: Command '{cmd_name}' not allowed. Allowed: {allowed_str}"
            )]

        # Execute with shell=False for security
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )

        output = result.stdout.strip() if result.stdout else result.stderr.strip()

        if result.returncode != 0 and not output:
            output = f"Command exited with code {result.returncode}"

        return [TextContent(type="text", text=output)]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text=f"Error: Command timeout after {timeout}s")]
    except FileNotFoundError:
        return [TextContent(type="text", text=f"Error: Command not found: {cmd_name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: Execution failed: {e}")]


# ============================================================================
# Calculator Implementation
# ============================================================================

# Safe binary operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

# Safe unary operators
SAFE_UNARY_OPERATORS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe mathematical functions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
}

# Safe constants
SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _eval_node(node: ast.AST) -> Union[int, float]:
    """Recursively evaluate AST nodes safely."""
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Only numbers allowed, got: {type(node.value).__name__}")
        return node.value

    elif isinstance(node, ast.Num):
        return node.n

    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op = SAFE_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
        return op(left, right)

    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op = SAFE_UNARY_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
        return op(operand)

    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed")

        func_name = node.func.id
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Function not allowed: {func_name}")

        args = [_eval_node(arg) for arg in node.args]
        return SAFE_FUNCTIONS[func_name](*args)

    elif isinstance(node, ast.Name):
        if node.id not in SAFE_CONSTANTS:
            raise ValueError(f"Variable/constant not allowed: {node.id}")
        return SAFE_CONSTANTS[node.id]

    else:
        raise ValueError(f"Expression type not allowed: {type(node).__name__}")


def _safe_eval(expression: str) -> Union[int, float]:
    """Safely evaluate mathematical expression using AST parsing."""
    try:
        tree = ast.parse(expression, mode="eval")
        return _eval_node(tree.body)
    except SyntaxError as e:
        raise ValueError(f"Invalid syntax: {e}")
    except Exception as e:
        raise ValueError(str(e))


async def _calculator(expression: str) -> list[TextContent]:
    """Evaluate a mathematical expression safely."""
    try:
        expr = expression.strip()

        if not expr:
            return [TextContent(type="text", text="Error: Empty expression")]

        # Replace ^ with ** for exponentiation
        expr = expr.replace("^", "**")

        # Evaluate using AST
        result = _safe_eval(expr)

        # Format result
        if isinstance(result, float):
            if result.is_integer():
                output = str(int(result))
            else:
                output = f"{result:.10f}".rstrip("0").rstrip(".")
        else:
            output = str(result)

        return [TextContent(type="text", text=f"{expression} = {output}")]

    except ZeroDivisionError:
        return [TextContent(type="text", text="Error: Division by zero")]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: Calculation failed: {e}")]


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
