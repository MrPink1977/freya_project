# Freya Tools System

Freya now includes a comprehensive toolkit that allows her to interact with files, perform calculations, search the web, and more!

## Available Tools

### ⏰ Time & Date Tools

**get_current_time**
- Get the current time in any timezone
- Supports 12h and 24h formats
- Example: `timezone='America/New_York', format='12h'`

**get_current_date**
- Get the current date in various formats
- Formats: 'long', 'short', 'iso'
- Example: `format='long'` → "Monday, November 17, 2025"

**calculate_time_until**
- Calculate time remaining until a future date
- Takes ISO format dates: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
- Example: `target_date='2025-12-25'`

### 🧮 Calculator

**calculator**
- Evaluate mathematical expressions safely
- Supports: +, -, *, /, ^(power), sqrt, sin, cos, tan, log, pi, e, etc.
- Examples:
  - `expression='2 + 2 * 3'` → 8
  - `expression='sqrt(16) + 10'` → 14
  - `expression='sin(pi/2)'` → 1.0

### 📁 File Operations

**list_files**
- List files and directories
- Parameters:
  - `path`: Directory path (default: current directory)
  - `pattern`: File pattern like '*.py', '*.txt' (default: '*')
  - `recursive`: Search subdirectories (default: False)
  - `show_hidden`: Show hidden files (default: False)

**read_file**
- Read contents of a text file
- Parameters:
  - `path`: File path
  - `max_lines`: Maximum lines to read (default: 100)

**write_file**
- Write content to a file
- Parameters:
  - `path`: File path (creates parent directories if needed)
  - `content`: Text content to write
  - `append`: Append instead of overwrite (default: False)

### 🌐 Web Tools

**web_search**
- Search the web using DuckDuckGo
- Parameters:
  - `query`: Search query
  - `max_results`: Number of results (1-10, default: 5)

**web_scraper**
- Scrape and extract content from web pages
- Parameters:
  - `url`: URL to scrape
  - `mode`: What to extract:
    - `'text'` - Main content (default)
    - `'title'` - Page title
    - `'links'` - All links on page
    - `'headings'` - All h1-h6 headings
    - `'custom'` - Use CSS selector
  - `selector`: CSS selector for custom mode (e.g., '.article', '#main')
  - `max_length`: Max content length (default: 5000 chars)

### 💻 System Tools

**system_info**
- Get system information
- Parameters:
  - `info_type`: Type of info to retrieve:
    - `'all'` - Everything (default)
    - `'os'` - Operating system details
    - `'python'` - Python version and path
    - `'disk'` - Disk space usage
    - `'uptime'` - System uptime (Linux only)

**execute_command**
- Execute safe shell commands (whitelisted for security)
- Allowed commands: ls, dir, pwd, date, whoami, hostname, uptime, df, du, which, echo, cat, head, tail, wc, grep, find
- Parameters:
  - `command`: Command to execute
  - `timeout`: Timeout in seconds (default: 5)

## Using Tools in Code

```python
from freya.tools import ToolManager

# Create manager
manager = ToolManager()

# List available tools
print(manager.get_tools_description())

# Execute a tool
result = manager.execute_tool(
    "calculator",
    expression="sqrt(144) + 10"
)

if result.success:
    print(result.output)  # "sqrt(144) + 10 = 22"
else:
    print(f"Error: {result.error}")
```

## Creating Custom Tools

You can create custom tools by extending the `FreyaTool` base class:

```python
from freya.tools import FreyaTool, ToolResult

class MyCustomTool(FreyaTool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "What my tool does"

    def execute(self, **kwargs) -> ToolResult:
        try:
            # Do something
            output = "Success!"
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

# Register with manager
manager = ToolManager()
manager.register_tool(MyCustomTool())
```

## Tool Security

- **File Operations**: Proper path validation and permissions checking
- **Web Scraper**: User-agent header, timeout protection, content limits
- **Calculator**: Sandboxed eval with whitelist of safe functions only
- **Execute Command**: Strict whitelist of allowed commands
- **All Tools**: Exception handling and error reporting

## Dependencies

Required for full functionality:
- `beautifulsoup4>=4.12.0` - Web scraping
- `duckduckgo-search>=6.0.0` - Web search
- `requests>=2.31.0` - HTTP requests

All dependencies are included in `requirements.txt`.

## Examples

See `demo_tools.py` for a complete demonstration of all tools in action:

```bash
python demo_tools.py
```

## Integration with Freya

Tools can be integrated into the Freya orchestrator to allow the AI to use them during conversations. See the orchestrator integration guide for details.
