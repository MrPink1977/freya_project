"""
MCP Server Runner for Freya

This script discovers, configures, and runs all MCP servers for Freya.
It uses the official MCP Python SDK's transport and server management capabilities.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Note: This script must be run as a module to avoid circular imports
# Usage: python -m freya.run_mcp_servers <server_name>


# Available MCP servers
AVAILABLE_SERVERS = {
    "system": "freya.mcp_servers.system_server",
    "file": "freya.mcp_servers.file_server",
    "web": "freya.mcp_servers.web_server",
    "audio": "freya.mcp_servers.audio_server",
    "vision": "freya.mcp_servers.vision_server",
}


async def run_server(server_name: str) -> None:
    """
    Run a specific MCP server.
    
    Args:
        server_name: Name of the server to run (e.g., 'system', 'file', 'web')
    """
    if server_name not in AVAILABLE_SERVERS:
        print(f"Error: Unknown server '{server_name}'", file=sys.stderr)
        print(f"Available servers: {', '.join(AVAILABLE_SERVERS.keys())}", file=sys.stderr)
        sys.exit(1)
    
    module_path = AVAILABLE_SERVERS[server_name]
    
    try:
        # Dynamically import the server module
        module_parts = module_path.split(".")
        module = __import__(module_path, fromlist=[module_parts[-1]])
        
        # Get the server instance
        if not hasattr(module, "server"):
            print(f"Error: Module {module_path} does not have a 'server' attribute", file=sys.stderr)
            sys.exit(1)
        
        server = module.server
        
        # Run the server using stdio transport
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    except ImportError as e:
        print(f"Error: Failed to import server module {module_path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to run server {server_name}: {e}", file=sys.stderr)
        sys.exit(1)


def list_servers() -> None:
    """List all available MCP servers."""
    print("Available MCP Servers:")
    print("-" * 40)
    for name, module in AVAILABLE_SERVERS.items():
        print(f"  {name:10} -> {module}")
    print()
    print("Usage:")
    print(f"  python -m freya.run_mcp_servers <server_name>")
    print(f"  python -m freya.run_mcp_servers system")


def main() -> None:
    """Main entry point for the MCP server runner."""
    if len(sys.argv) < 2:
        list_servers()
        sys.exit(1)
    
    server_name = sys.argv[1]
    
    if server_name in ("--list", "-l", "list"):
        list_servers()
        sys.exit(0)
    
    if server_name in ("--help", "-h", "help"):
        list_servers()
        sys.exit(0)
    
    # Run the specified server
    asyncio.run(run_server(server_name))


if __name__ == "__main__":
    main()
