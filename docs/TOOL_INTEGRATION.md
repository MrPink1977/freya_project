# Integrating Tools into Freya's Orchestrator

This guide explains how to make Freya's new tools available during conversations.

## Quick Start

### Option 1: Simple Integration (Recommended to start)

Add tool manager to the orchestrator and expose specific tools:

```python
# In orchestrator.py __init__
from .tools import ToolManager

self._tool_manager = ToolManager()

# Add method to orchestrator
def use_tool(self, tool_name: str, **kwargs) -> str:
    """Use a tool and return result."""
    result = self._tool_manager.execute_tool(tool_name, **kwargs)
    return result.output if result.success else f"Tool failed: {result.error}"
```

### Option 2: LLM Function Calling

Make tools available to the LLM as functions it can call:

```python
def _get_tool_definitions(self) -> list[dict]:
    """Convert tools to LLM function definitions."""
    functions = []
    for tool in self._tool_manager.list_tools(enabled_only=True):
        functions.append({
            "name": tool.name,
            "description": tool.description,
            # Add parameters based on tool
        })
    return functions

# Add to LLM request
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_input}
]
functions = self._get_tool_definitions()

# Send to Ollama with function calling support
response = self._client.chat(messages, functions=functions)
```

### Option 3: Manual Tool Triggers

Detect tool usage patterns in user input:

```python
def _detect_tool_request(self, user_input: str) -> tuple[str | None, dict]:
    """Detect if user is requesting a tool."""

    # Time queries
    if re.search(r'what (time|date)', user_input, re.I):
        return ("get_current_time", {"timezone": "UTC"})

    # Calculator
    if re.search(r'calculate|compute|what is \d', user_input, re.I):
        # Extract expression
        return ("calculator", {"expression": expr})

    # File operations
    if re.search(r'list files|show files', user_input, re.I):
        return ("list_files", {"path": "."})

    # Web search
    if re.search(r'search (for|the web)', user_input, re.I):
        query = # extract query
        return ("web_search", {"query": query})

    return (None, {})

# In conversation handler
tool_name, kwargs = self._detect_tool_request(user_input)
if tool_name:
    result = self._tool_manager.execute_tool(tool_name, **kwargs)
    # Add result to context or speak it
```

## Example Integration Points

### 1. System Prompt Addition

Tell Freya about available tools:

```python
system_prompt = f"""You are Freya, a helpful voice assistant.

You have access to the following tools:
{self._tool_manager.get_tools_description()}

When a user asks you to do something these tools can help with, use them!
"""
```

### 2. Add Tools to Context

Include tool results in conversation history:

```python
# User asks: "What time is it in Tokyo?"
result = self._tool_manager.execute_tool(
    "get_current_time",
    timezone="Asia/Tokyo"
)

# Add to context
self._context.add_message("system", f"[Tool: get_current_time] {result.output}")
# Now LLM has this info to respond naturally
```

### 3. Proactive Tool Use

Freya can offer to use tools:

```python
# User: "I need to finish my homework"
# Freya: "Would you like me to set a timer to help you stay focused?"

if user_confirms:
    result = self._tool_manager.execute_tool("set_timer", seconds=1800)
```

## Testing Integration

Create a simple test in the orchestrator:

```python
def test_tool_integration(self):
    """Test that tools work in the orchestrator."""
    result = self._tool_manager.execute_tool("calculator", expression="2+2")
    assert result.success
    assert "4" in result.output
```

## Next Steps

1. **Start Simple**: Add the tool manager to orchestrator
2. **Test Manual**: Use `self._tool_manager.execute_tool()` directly
3. **Add Patterns**: Detect common tool use cases
4. **Integrate LLM**: Use function calling if Ollama supports it
5. **Expand**: Add more tools as needed

## Advanced: Custom Tool Responses

Make tool responses conversational:

```python
def _format_tool_response(self, tool_name: str, result: ToolResult) -> str:
    """Make tool output conversational."""

    if tool_name == "calculator":
        return f"That equals {result.output}"

    elif tool_name == "get_current_time":
        return f"It's currently {result.output}"

    elif tool_name == "list_files":
        file_count = result.metadata.get("file_count", 0)
        return f"I found {file_count} files:\n{result.output}"

    else:
        return result.output
```

## Security Considerations

- Tools are already sandboxed (calculator, file ops, command execution)
- Consider rate limiting for web tools
- Monitor tool usage in logs
- Users can disable specific tools via `tool.disable()`

## Performance Tips

- Tools are lazy-loaded (only imported when first used)
- Web tools have timeouts (5-10s)
- File tools have size limits
- Calculator is very fast (no I/O)
