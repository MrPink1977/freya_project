# Freya MCP Integration Documentation

**Date:** December 2, 2025  
**Version:** 1.0.0  
**Status:** Phase 1 Complete

## Overview

This document describes the Model Context Protocol (MCP) integration for the Freya project. The integration uses the official `mcp` Python SDK to provide a standardized interface for Freya's tools and capabilities.

## Architecture

### MCP Server Structure

Freya's MCP implementation consists of five specialized servers, each handling a specific domain:

```
freya/mcp_servers/
├── __init__.py
├── system_server.py      # System info, command execution, calculator
├── file_server.py         # File operations with security
├── web_server.py          # Web search and scraping
├── audio_server.py        # Speech-to-text and text-to-speech (stub)
└── vision_server.py       # Facial recognition and camera control (stub)
```

### Server Runner

The `freya/run_mcp_servers.py` script provides a unified interface for running any MCP server:

```bash
python -m freya.run_mcp_servers <server_name>
```

## Available Servers

### 1. System Server (`freya-system`)

**Module:** `freya.mcp_servers.system_server`

**Tools:**
- `system_info` - Get system information (OS, Python, disk, uptime)
- `execute_command` - Execute safe shell commands with whitelist protection
- `calculator` - Evaluate mathematical expressions safely

**Security Features:**
- Command whitelist enforcement
- Injection pattern detection
- AST-based expression evaluation (no `eval()`)

**Usage:**
```bash
python -m freya.run_mcp_servers system
```

### 2. File Server (`freya-file`)

**Module:** `freya.mcp_servers.file_server`

**Tools:**
- `list_files` - List files and directories with pattern matching
- `read_file` - Read text files with type validation
- `write_file` - Write or append to files

**Security Features:**
- Path traversal protection
- Allowed directory enforcement
- File type validation (text-only)
- Size limits (1MB read, 10MB write)
- Binary file detection via magic bytes

**Allowed Directories:**
- `~/Documents`
- `~/Downloads`
- `~/Desktop`
- `<project>/data`
- `<project>/logs`

**Usage:**
```bash
python -m freya.run_mcp_servers file
```

### 3. Web Server (`freya-web`)

**Module:** `freya.mcp_servers.web_server`

**Tools:**
- `web_search` - Search DuckDuckGo with caching
- `web_scraper` - Extract content from web pages

**Features:**
- Search result caching (1 hour TTL)
- Multiple extraction modes (text, links, title, headings, custom)
- Content truncation and formatting
- Retry logic with exponential backoff

**Usage:**
```bash
python -m freya.run_mcp_servers web
```

### 4. Audio Server (`freya-audio`) [STUB]

**Module:** `freya.mcp_servers.audio_server`

**Tools:**
- `speech_to_text` - Convert speech to text (not implemented)
- `text_to_speech` - Convert text to speech (not implemented)

**Status:** Stub implementation. Requires integration with `freya.voice` module.

**Usage:**
```bash
python -m freya.run_mcp_servers audio
```

### 5. Vision Server (`freya-vision`) [STUB]

**Module:** `freya.mcp_servers.vision_server`

**Tools:**
- `detect_faces` - Detect and recognize faces (not implemented)
- `camera_control` - Control camera PTZ (not implemented)

**Status:** Stub implementation. Requires integration with `freya.vision` module.

**Usage:**
```bash
python -m freya.run_mcp_servers vision
```

## Configuration

### MCP Server Configuration

The `config/mcp_servers.json` file contains the configuration for all MCP servers:

```json
{
  "mcpServers": {
    "freya-system": {
      "command": "python",
      "args": ["-m", "freya.run_mcp_servers", "system"],
      "description": "System information and command execution tools"
    },
    ...
  }
}
```

### Client Configuration

To use Freya's MCP servers with an MCP client (e.g., Claude Desktop, Cline), add the following to your MCP client configuration:

**For Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):**

```json
{
  "mcpServers": {
    "freya-system": {
      "command": "python",
      "args": ["-m", "freya.run_mcp_servers", "system"],
      "cwd": "/path/to/freya_project"
    },
    "freya-file": {
      "command": "python",
      "args": ["-m", "freya.run_mcp_servers", "file"],
      "cwd": "/path/to/freya_project"
    },
    "freya-web": {
      "command": "python",
      "args": ["-m", "freya.run_mcp_servers", "web"],
      "cwd": "/path/to/freya_project"
    }
  }
}
```

## Installation

### Prerequisites

1. Python 3.11+
2. Official `mcp` Python SDK

### Install Dependencies

```bash
cd freya_project
pip install -e .
```

This will install the `mcp>=1.0.0` dependency specified in `pyproject.toml`.

### Verify Installation

```bash
# List available servers
python -m freya.run_mcp_servers --list

# Test a server (requires MCP client)
python -m freya.run_mcp_servers system
```

## Testing

### Manual Testing

Each server can be tested manually using the MCP CLI tool:

```bash
# Install MCP CLI
pip install mcp-cli

# Test system server
mcp-cli test python -m freya.run_mcp_servers system

# List tools
mcp-cli tools python -m freya.run_mcp_servers system

# Call a tool
mcp-cli call python -m freya.run_mcp_servers system system_info '{"info_type": "all"}'
```

### Automated Testing

Create test scripts in `tests/mcp/`:

```python
# tests/mcp/test_system_server.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_system_info():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "freya.run_mcp_servers", "system"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            assert len(tools.tools) == 3
            
            # Call system_info
            result = await session.call_tool("system_info", {"info_type": "os"})
            assert "OS:" in result.content[0].text

if __name__ == "__main__":
    asyncio.run(test_system_info())
```

## Migration Plan

This implementation represents **Phase 1** of the full MCP integration plan. The complete migration involves:

### Phase 1: Project Setup and SDK Integration ✅ COMPLETE
- ✅ Added `mcp` dependency to `pyproject.toml`
- ✅ Created `freya/mcp_servers/` directory
- ✅ Implemented `run_mcp_servers.py` runner script

### Phase 2: Tool Migration to MCP Servers ✅ COMPLETE
- ✅ System Server (system_info, execute_command, calculator)
- ✅ File Server (list_files, read_file, write_file)
- ✅ Web Server (web_search, web_scraper)
- ⚠️ Audio Server (stub implementation)
- ⚠️ Vision Server (stub implementation)

### Phase 3: Refactoring the Orchestration Layer 🔄 PENDING
- ⏳ Create `MCPClientAgent` to interact with MCP servers
- ⏳ Integrate with `DialogAgent` for unified tool access
- ⏳ Deprecate `ToolExecutorAgent` and regex-based tool detection

### Phase 4: Implementing Advanced MCP Features 🔄 PENDING
- ⏳ Implement Resources (conversation history, system metrics)
- ⏳ Implement Prompts (personality, system prompts)
- ⏳ Implement Elicitation (user input requests)
- ⏳ Implement Security and Consent (tool execution approval)

### Phase 5: Deprecation and Cleanup 🔄 PENDING
- ⏳ Remove custom MCP framework (`freya_mcp/`)
- ⏳ Remove legacy `Orchestrator`
- ⏳ Update documentation and diagrams

## Integration with Existing Freya Components

### Current State

The MCP servers are **standalone** and can be used independently of the main Freya application. They provide the same functionality as the existing `freya/tools/` modules but through a standardized MCP interface.

### Future Integration

In Phase 3, the `MCPClientAgent` will:
1. Connect to all MCP servers on startup
2. Discover available tools using `tools/list`
3. Provide a unified interface for `DialogAgent`
4. Execute tools via `tools/call` requests
5. Handle tool results and errors

This will allow Freya to use both:
- **Internal tools** via direct Python imports (current method)
- **MCP tools** via the MCP protocol (new method)

Eventually, all tools will migrate to MCP, and the internal tool system will be deprecated.

## Troubleshooting

### Server Won't Start

**Problem:** `ModuleNotFoundError: No module named 'mcp'`

**Solution:** Install the MCP SDK:
```bash
pip install mcp
```

### Import Errors

**Problem:** `ImportError: cannot import name 'Server' from 'mcp.server'`

**Solution:** Ensure you're using the correct MCP SDK version:
```bash
pip install --upgrade mcp
```

### Tool Execution Fails

**Problem:** Tool returns an error message

**Solution:** Check the tool's input schema and ensure all required parameters are provided. Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Path Access Denied (File Server)

**Problem:** `Access denied: path is outside allowed directories`

**Solution:** The file server restricts access to specific directories for security. Either:
1. Move files to an allowed directory (`~/Documents`, `~/Downloads`, etc.)
2. Modify `ALLOWED_DIRECTORIES` in `file_server.py` (not recommended)

### Command Not Allowed (System Server)

**Problem:** `Command 'xyz' not allowed`

**Solution:** The system server only allows whitelisted commands. To add a command:
1. Edit `system_server.py`
2. Add the command to `ALLOWED_COMMANDS`
3. Restart the server

## Best Practices

### Security

1. **Never disable security checks** in production
2. **Validate all user input** before passing to tools
3. **Use the principle of least privilege** for file access
4. **Monitor tool usage** for suspicious patterns
5. **Keep the MCP SDK updated** for security patches

### Performance

1. **Use caching** for expensive operations (web search)
2. **Set appropriate timeouts** for long-running tools
3. **Limit result sizes** to avoid memory issues
4. **Use async operations** where possible

### Development

1. **Test servers independently** before integration
2. **Use type hints** for better IDE support
3. **Follow the existing code style** (Ruff, Black)
4. **Document all tools** with clear descriptions
5. **Add error handling** for all edge cases

## Contributing

To add a new MCP server:

1. Create a new file in `freya/mcp_servers/`
2. Implement the server using the MCP SDK
3. Add the server to `AVAILABLE_SERVERS` in `run_mcp_servers.py`
4. Update `config/mcp_servers.json`
5. Add tests in `tests/mcp/`
6. Update this documentation

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Freya Project](https://github.com/MrPink1977/freya_project)
- [Original Plan of Action](../FreyaProject_MCPIntegrationPlanofAction.md)

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [MCP SDK documentation](https://github.com/modelcontextprotocol/python-sdk)
3. Open an issue on [GitHub](https://github.com/MrPink1977/freya_project/issues)

## License

This integration is part of the Freya project and is licensed under the MIT License.
