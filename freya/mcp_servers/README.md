# Freya MCP Servers

This directory contains the MCP (Model Context Protocol) server implementations for Freya.

## Quick Start

### Run a Server

```bash
# From project root
python -m freya.run_mcp_servers system
```

### List Available Servers

```bash
python -m freya.run_mcp_servers --list
```

## Available Servers

| Server | Status | Tools | Description |
|--------|--------|-------|-------------|
| `system` | ✅ Ready | 3 | System info, commands, calculator |
| `file` | ✅ Ready | 3 | File operations with security |
| `web` | ✅ Ready | 2 | Web search and scraping |
| `audio` | ⚠️ Stub | 2 | Speech-to-text, text-to-speech |
| `vision` | ⚠️ Stub | 2 | Face detection, camera control |

## Server Details

### System Server

**Tools:**
- `system_info` - Get OS, Python, disk, uptime info
- `execute_command` - Run whitelisted shell commands
- `calculator` - Evaluate math expressions

**Security:** Whitelist + injection protection

### File Server

**Tools:**
- `list_files` - List directory contents
- `read_file` - Read text files
- `write_file` - Write/append to files

**Security:** Path traversal protection, type validation, size limits

### Web Server

**Tools:**
- `web_search` - Search DuckDuckGo
- `web_scraper` - Extract web page content

**Features:** Caching, retry logic, multiple extraction modes

### Audio Server (Stub)

**Tools:**
- `speech_to_text` - STT (not implemented)
- `text_to_speech` - TTS (not implemented)

**Status:** Requires integration with `freya.voice` module

### Vision Server (Stub)

**Tools:**
- `detect_faces` - Face detection (not implemented)
- `camera_control` - Camera PTZ (not implemented)

**Status:** Requires integration with `freya.vision` module

## Development

### Adding a New Server

1. Create `<name>_server.py` in this directory
2. Implement using MCP SDK:

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("freya-<name>-server")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [...]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    ...

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

3. Add to `AVAILABLE_SERVERS` in `run_mcp_servers.py`
4. Update `config/mcp_servers.json`
5. Add tests

### Testing

```bash
# Manual test
python -m freya.run_mcp_servers system

# With MCP CLI
mcp-cli test python -m freya.run_mcp_servers system
```

## Documentation

See [docs/MCP_INTEGRATION.md](../../docs/MCP_INTEGRATION.md) for complete documentation.

## License

MIT License - Part of the Freya Project
