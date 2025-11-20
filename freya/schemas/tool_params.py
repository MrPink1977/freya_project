"""
Pydantic schemas for tool parameters.

Validates parameters passed to individual tools, ensuring type safety
and preventing invalid inputs before tool execution.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, HttpUrl


class CalculatorParams(BaseModel):
    """Parameters for calculator tool."""
    
    expression: str = Field(min_length=1, max_length=500, description="Mathematical expression")


class GetCurrentTimeParams(BaseModel):
    """Parameters for get_current_time tool."""
    
    timezone: Optional[str] = Field(None, max_length=100, description="Timezone (e.g., 'America/New_York', 'UTC')")
    format: Literal["12h", "24h"] = Field("12h", description="Time format")
    
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        """Validate timezone against zoneinfo database."""
        if v is None:
            return v
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
            return v
        except Exception:
            raise ValueError(f"Invalid timezone: {v}")


class GetCurrentDateParams(BaseModel):
    """Parameters for get_current_date tool."""
    
    format: Literal["long", "short", "iso"] = Field("long", description="Date format")


class ListFilesParams(BaseModel):
    """Parameters for list_files tool."""
    
    directory: str = Field(".", max_length=500, description="Directory path")
    pattern: str = Field("*", max_length=100, description="File pattern (e.g., '*.py')")
    recursive: bool = Field(False, description="Search recursively")
    show_hidden: bool = Field(False, description="Show hidden files")


class ReadFileParams(BaseModel):
    """Parameters for read_file tool."""
    
    filepath: str = Field(min_length=1, max_length=500, description="File path to read")
    max_lines: int = Field(100, ge=1, le=10000, description="Maximum lines to read")


class WriteFileParams(BaseModel):
    """Parameters for write_file tool."""
    
    filepath: str = Field(min_length=1, max_length=500, description="File path to write")
    content: str = Field(max_length=1000000, description="Content to write (max 1MB)")
    append: bool = Field(False, description="Append to existing file")


class ExecuteCommandParams(BaseModel):
    """Parameters for run_command tool."""
    
    command: str = Field(min_length=1, max_length=500, description="System command to execute")
    timeout: int = Field(5, ge=1, le=60, description="Command timeout in seconds")


class SystemInfoParams(BaseModel):
    """Parameters for system_info tool."""
    
    info_type: Literal["all", "os", "python", "disk", "uptime"] = Field("all", description="Type of system info")


class WebSearchParams(BaseModel):
    """Parameters for web_search tool."""
    
    query: str = Field(min_length=1, max_length=500, description="Search query")
    max_results: int = Field(5, ge=1, le=10, description="Maximum search results")


class WebScraperParams(BaseModel):
    """Parameters for web_scraper tool."""
    
    url: HttpUrl = Field(description="URL to scrape")
    mode: Literal["text", "links", "title", "headings", "custom"] = Field("text", description="Scraping mode")
    selector: Optional[str] = Field(None, max_length=200, description="CSS selector (for custom mode)")
    max_length: int = Field(5000, ge=100, le=50000, description="Maximum content length")


class PerformanceMonitorParams(BaseModel):
    """Parameters for performance_monitor tool."""
    
    metric: Literal["all", "cpu", "memory", "disk", "network", "processes", "gpu"] = Field("all", description="Performance metric to monitor")
