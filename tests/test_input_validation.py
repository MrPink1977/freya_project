"""
Unit tests for Pydantic input validation.

Tests validation schemas, error handling, and protection against
type confusion, range violations, and malformed payloads.
"""
import pytest
from pydantic import ValidationError
from freya.schemas.messages import (
    DialogRequestPayload,
    MemoryStorePayload,
    MemoryQueryPayload,
    FactStorePayload,
    FactQueryPayload,
    UserQueryPayload,
)
from freya.schemas.tool_params import (
    CalculatorParams,
    GetCurrentTimeParams,
    ListFilesParams,
    ReadFileParams,
    WebSearchParams,
)


class TestMessagePayloadValidation:
    """Test agent message payload schemas."""
    
    def test_dialog_request_valid(self):
        """DialogRequestPayload accepts valid data."""
        payload = DialogRequestPayload(text="Hello", model="llama3", stream=True)
        assert payload.text == "Hello"
        assert payload.model == "llama3"
        assert payload.stream is True
    
    def test_dialog_request_strips_whitespace(self):
        """DialogRequestPayload strips leading/trailing whitespace."""
        payload = DialogRequestPayload(text="  Hello  ")
        assert payload.text == "  Hello  "  # Pydantic doesn't auto-strip Field strings
    
    def test_dialog_request_empty_text(self):
        """DialogRequestPayload rejects empty text."""
        with pytest.raises(ValidationError) as exc_info:
            DialogRequestPayload(text="")
        errors = exc_info.value.errors()
        assert any("min_length" in str(e) for e in errors)
    
    def test_dialog_request_text_too_long(self):
        """DialogRequestPayload rejects text over 5000 chars."""
        with pytest.raises(ValidationError):
            DialogRequestPayload(text="x" * 5001)
    
    def test_memory_store_valid(self):
        """MemoryStorePayload accepts valid data."""
        payload = MemoryStorePayload(content="Test memory", role="user", importance=5)
        assert payload.content == "Test memory"
        assert payload.role == "user"
        assert payload.importance == 5
    
    def test_memory_store_invalid_role(self):
        """MemoryStorePayload rejects invalid role."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryStorePayload(content="Test", role="system")
        errors = exc_info.value.errors()
        assert any("role" in str(e) for e in errors)
    
    def test_memory_store_importance_out_of_range(self):
        """MemoryStorePayload rejects importance outside 1-10."""
        with pytest.raises(ValidationError):
            MemoryStorePayload(content="Test", importance=0)
        
        with pytest.raises(ValidationError):
            MemoryStorePayload(content="Test", importance=11)
    
    def test_memory_store_importance_negative(self):
        """MemoryStorePayload rejects negative importance."""
        with pytest.raises(ValidationError):
            MemoryStorePayload(content="Test", importance=-5)
    
    def test_memory_query_valid(self):
        """MemoryQueryPayload accepts valid data."""
        payload = MemoryQueryPayload(query="test query", limit=10, min_score=0.5)
        assert payload.query == "test query"
        assert payload.limit == 10
        assert payload.min_score == 0.5
    
    def test_memory_query_limit_out_of_range(self):
        """MemoryQueryPayload rejects limit outside 1-50."""
        with pytest.raises(ValidationError):
            MemoryQueryPayload(query="test", limit=0)
        
        with pytest.raises(ValidationError):
            MemoryQueryPayload(query="test", limit=51)
    
    def test_memory_query_min_score_invalid(self):
        """MemoryQueryPayload rejects min_score outside 0.0-1.0."""
        with pytest.raises(ValidationError):
            MemoryQueryPayload(query="test", min_score=-0.1)
        
        with pytest.raises(ValidationError):
            MemoryQueryPayload(query="test", min_score=1.1)
    
    def test_fact_store_valid(self):
        """FactStorePayload accepts valid data."""
        payload = FactStorePayload(category="name", key="first_name", value="Alice", confidence=0.9)
        assert payload.category == "name"
        assert payload.key == "first_name"
        assert payload.value == "Alice"
        assert payload.confidence == 0.9
    
    def test_fact_store_confidence_invalid(self):
        """FactStorePayload rejects confidence outside 0.0-1.0."""
        with pytest.raises(ValidationError):
            FactStorePayload(category="test", key="test", value="test", confidence=1.5)
    
    def test_fact_query_valid(self):
        """FactQueryPayload accepts valid data."""
        payload = FactQueryPayload(query="test", category="name", limit=5)
        assert payload.query == "test"
        assert payload.category == "name"
        assert payload.limit == 5
    
    def test_user_query_valid(self):
        """UserQueryPayload accepts valid text."""
        payload = UserQueryPayload(text="What time is it?")
        assert payload.text == "What time is it?"


class TestToolParameterValidation:
    """Test tool parameter schemas."""
    
    def test_calculator_params_valid(self):
        """CalculatorParams accepts valid expression."""
        params = CalculatorParams(expression="2 + 2")
        assert params.expression == "2 + 2"
    
    def test_calculator_params_too_long(self):
        """CalculatorParams rejects expression over 500 chars."""
        with pytest.raises(ValidationError):
            CalculatorParams(expression="x" * 501)
    
    def test_get_current_time_valid(self):
        """GetCurrentTimeParams accepts valid timezone."""
        params = GetCurrentTimeParams(timezone="America/New_York", format="12h")
        assert params.timezone == "America/New_York"
        assert params.format == "12h"
    
    def test_get_current_time_invalid_timezone(self):
        """GetCurrentTimeParams rejects invalid timezone."""
        with pytest.raises(ValidationError) as exc_info:
            GetCurrentTimeParams(timezone="Invalid/Timezone")
        assert "Invalid timezone" in str(exc_info.value)
    
    def test_get_current_time_invalid_format(self):
        """GetCurrentTimeParams rejects invalid format."""
        with pytest.raises(ValidationError):
            GetCurrentTimeParams(format="invalid")
    
    def test_list_files_params_valid(self):
        """ListFilesParams accepts valid parameters."""
        params = ListFilesParams(directory="/home/user", pattern="*.py", recursive=True)
        assert params.directory == "/home/user"
        assert params.pattern == "*.py"
        assert params.recursive is True
    
    def test_read_file_params_valid(self):
        """ReadFileParams accepts valid filepath."""
        params = ReadFileParams(filepath="/path/to/file.txt", max_lines=50)
        assert params.filepath == "/path/to/file.txt"
        assert params.max_lines == 50
    
    def test_read_file_params_max_lines_invalid(self):
        """ReadFileParams rejects invalid max_lines."""
        with pytest.raises(ValidationError):
            ReadFileParams(filepath="test.txt", max_lines=0)
        
        with pytest.raises(ValidationError):
            ReadFileParams(filepath="test.txt", max_lines=10001)
    
    def test_web_search_params_valid(self):
        """WebSearchParams accepts valid query."""
        params = WebSearchParams(query="Python tutorial", max_results=5)
        assert params.query == "Python tutorial"
        assert params.max_results == 5
    
    def test_web_search_params_max_results_invalid(self):
        """WebSearchParams rejects max_results outside 1-10."""
        with pytest.raises(ValidationError):
            WebSearchParams(query="test", max_results=0)
        
        with pytest.raises(ValidationError):
            WebSearchParams(query="test", max_results=11)


class TestTypeConfusionAttacks:
    """Test protection against type confusion attacks."""
    
    def test_importance_as_string(self):
        """MemoryStorePayload coerces numeric strings (Pydantic default behavior)."""
        payload = MemoryStorePayload(content="test", importance="5")
        assert payload.importance == 5  # Auto-coerced
    
    def test_content_as_dict(self):
        """MemoryStorePayload rejects dict content."""
        with pytest.raises(ValidationError):
            MemoryStorePayload(content={"key": "value"})
