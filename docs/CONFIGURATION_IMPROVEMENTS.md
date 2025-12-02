# Configuration System Improvements

**Status**: ✅ COMPLETE
**Date**: 2025-12-02
**Branch**: `claude/code-quality-improvements-01DfQmKpX`

## Summary

Converted Freya's configuration system from manual dataclass validation to Pydantic BaseModel with automatic validation. This provides:

1. ✅ **Automatic validation** - Pydantic validates all fields automatically
2. ✅ **Better error messages** - Clear, specific validation errors
3. ✅ **Type safety** - Runtime type checking
4. ✅ **Less boilerplate** - Eliminated ~100 lines of manual validation
5. ✅ **Comprehensive documentation** - Every class and field documented
6. ✅ **Fail-fast behavior** - Invalid configuration caught at load time

## Changes

### Old System (`config.py`)

**Problems:**
- Manual validation scattered throughout 200+ line `load_settings()` function
- Custom validation functions (`_validate_range`, `_validate_positive`, etc.)
- No field-level documentation
- Verbose error handling code
- Type checking only at static analysis time

**Example (old):**
```python
@dataclass(frozen=True)
class SpeechToTextConfig:
    model: str
    device: str
    sample_rate: int
    silence_threshold: float
    # ... more fields

# Manual validation:
stt_sample_rate = int(stt_raw.get("sample_rate", 16000))
stt_silence_threshold = float(stt_raw.get("silence_threshold", 0.02))
_validate_positive(stt_sample_rate, "sample_rate", "stt")
_validate_range(stt_silence_threshold, 0.0, 1.0, "silence_threshold", "stt")
```

### New System (`config_v2.py`)

**Benefits:**
- Automatic validation using Pydantic `Field` constraints
- Self-documenting with docstrings on every model
- Declarative validators using decorators
- Environment variable overrides in dedicated function
- Clean separation of concerns

**Example (new):**
```python
class SpeechToTextConfig(BaseModel):
    """Speech-to-text configuration using faster-whisper.

    Attributes:
        model: Whisper model name (e.g., 'base', 'small', 'medium')
        sample_rate: Audio sample rate in Hz
        silence_threshold: RMS threshold for silence detection (0.0-1.0)
        # ... more documented fields
    """

    model: str = Field(default="base")
    device: str = Field(default="auto")
    sample_rate: int = Field(default=16000, gt=0)
    silence_threshold: float = Field(default=0.02, ge=0.0, le=1.0)

    class Config:
        frozen = True
```

## Key Improvements

### 1. Declarative Validation

**Before:**
```python
def _validate_range(value: float, min_val: float, max_val: float, field_name: str):
    if not (min_val <= value <= max_val):
        raise ConfigValidationError(f"{field_name} must be between {min_val} and {max_val}")

stt_silence_threshold = float(stt_raw.get("silence_threshold", 0.02))
_validate_range(stt_silence_threshold, 0.0, 1.0, "silence_threshold", "stt")
```

**After:**
```python
silence_threshold: float = Field(default=0.02, ge=0.0, le=1.0)
```

### 2. Custom Validators

**Before:**
```python
startup_mode_raw = str(app_raw.get("startup_mode", "normal")).strip().lower()
if startup_mode_raw not in {"normal", "diagnostic"}:
    logger.warning("Invalid startup_mode '%s', defaulting to 'normal'", startup_mode_raw)
    startup_mode_raw = "normal"
```

**After:**
```python
@field_validator("startup_mode")
@classmethod
def validate_startup_mode(cls, v: str) -> str:
    """Validate startup mode."""
    v = v.strip().lower()
    if v not in ["normal", "diagnostic"]:
        logger.warning("Invalid startup_mode '%s', defaulting to 'normal'", v)
        return "normal"
    return v
```

### 3. Environment Variable Overrides

**Before:** Scattered throughout `load_settings()` function

**After:** Centralized in `_apply_env_overrides()` function
```python
def _apply_env_overrides(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to raw configuration."""
    if "OLLAMA_HOST" in os.environ:
        raw.setdefault("ollama", {})["host"] = os.environ["OLLAMA_HOST"]
    # ... more overrides
    return raw
```

### 4. Comprehensive Documentation

Every model now includes:
- Class docstring explaining purpose
- Field descriptions with examples
- Validator docstrings
- Type hints with constraints

**Example:**
```python
class OllamaConfig(BaseModel):
    """Ollama LLM configuration.

    Attributes:
        host: Ollama server URL (e.g., http://localhost:11434)
        model: Model name (e.g., llama3.2:3b)
        options: Additional model options passed to Ollama API
    """

    host: str = Field(default="http://localhost:11434", min_length=1)
    model: str = Field(default="llama3.2:3b", min_length=1)
    options: Dict[str, Any] = Field(default_factory=dict)
```

### 5. Better Error Messages

**Before:**
```
ConfigValidationError: Configuration error: stt.silence_threshold must be between 0.0 and 1.0, got 1.5
```

**After (Pydantic):**
```
ValidationError: 1 validation error for Settings
stt -> silence_threshold
  Input should be less than or equal to 1.0 [type=less_than_equal, input_value=1.5]
```

## Validation Features

### Built-in Constraints

Pydantic provides automatic validation for:
- `gt` / `ge`: Greater than / greater than or equal
- `lt` / `le`: Less than / less than or equal
- `min_length` / `max_length`: String length constraints
- `regex`: Pattern matching
- Type coercion: Automatic conversion to declared types

**Examples:**
```python
max_history: int = Field(default=10, gt=0)  # Must be > 0
wake_word: str = Field(default="Hey, Freya", min_length=1)  # Non-empty
wake_sensitivity: float = Field(default=0.75, ge=0.0, le=1.0)  # 0.0-1.0 range
```

### Custom Validators

Field-level and model-level validators:
```python
@field_validator("store_type")
@classmethod
def validate_store_type(cls, v: str) -> str:
    """Validate storage type is supported."""
    if v not in ["chroma", "sqlite"]:
        raise ValueError(f"store_type must be 'chroma' or 'sqlite', got '{v}'")
    return v

@model_validator(mode="after")
def sync_max_history(self) -> "Settings":
    """Sync app.max_history with memory.short_term.max_history."""
    # Cross-field validation logic
    return self
```

## Migration Plan

### Phase 1: Side-by-side (Current)
- ✅ Keep `config.py` (old) for backward compatibility
- ✅ Add `config_v2.py` (new) with Pydantic
- Test both systems in parallel

### Phase 2: Gradual Migration
- Update imports to use `config_v2`
- Test all modules with new config
- Verify no regressions

### Phase 3: Deprecation
- Mark `config.py` as deprecated
- Add migration warnings
- Update all documentation

### Phase 4: Cleanup
- Remove `config.py`
- Rename `config_v2.py` → `config.py`
- Final testing

## Testing

### Validation Tests

```python
from freya.core.config_v2 import Settings, ConfigValidationError
from pydantic import ValidationError

# Test valid configuration
settings = Settings(
    ollama={"host": "http://localhost:11434", "model": "llama3.2:3b"}
)
assert settings.ollama.model == "llama3.2:3b"

# Test validation failure
try:
    Settings(stt={"sample_rate": -1})  # Invalid: must be > 0
except ValidationError as e:
    print(e)  # Clear error message
```

### Environment Variable Tests

```python
import os
from freya.core.config_v2 import load_settings

os.environ["OLLAMA_MODEL"] = "llama3.2:1b"
settings = load_settings()
assert settings.ollama.model == "llama3.2:1b"  # Override applied
```

## File Comparison

| Metric | Old (`config.py`) | New (`config_v2.py`) |
|--------|-------------------|----------------------|
| Total Lines | 431 | 527 |
| Code Lines | ~350 | ~200 |
| Documentation Lines | ~50 | ~300 |
| Manual Validation | ~100 lines | 0 lines |
| Dataclasses | 10 | 0 |
| Pydantic Models | 0 | 10 |
| Docstrings | Minimal | Comprehensive |

**Note:** New version has MORE lines due to comprehensive documentation, but LESS functional code due to automatic validation.

## Benefits Summary

### Developer Experience
- ✅ Self-documenting configuration models
- ✅ IDE autocomplete for all fields
- ✅ Clear error messages when validation fails
- ✅ Type safety at runtime

### Maintainability
- ✅ Less boilerplate code
- ✅ Centralized validation logic
- ✅ Easy to add new fields
- ✅ Consistent structure

### Reliability
- ✅ Fail-fast on invalid configuration
- ✅ Automatic type coercion
- ✅ Prevents runtime errors from bad config
- ✅ Validated defaults for all fields

### Code Quality
- ✅ Eliminates manual validation functions
- ✅ Declarative instead of imperative
- ✅ Follows Pydantic best practices
- ✅ Industry-standard approach

## Example Usage

### Loading Configuration

```python
from freya.core.config_v2 import load_settings

# Load from default path (config/default.yaml)
settings = load_settings()

# Load from custom path
from pathlib import Path
settings = load_settings(Path("config/production.yaml"))

# Access validated configuration
print(f"Using model: {settings.ollama.model}")
print(f"Wake word: {settings.app.wake_word}")
print(f"Max history: {settings.memory.short_term.max_history}")
```

### Error Handling

```python
from freya.core.config_v2 import load_settings, ConfigValidationError
from pydantic import ValidationError

try:
    settings = load_settings()
except FileNotFoundError as e:
    print(f"Configuration file not found: {e}")
except ValidationError as e:
    print(f"Invalid configuration:")
    for error in e.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        print(f"  {field}: {error['msg']}")
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
```

## Future Enhancements

### 1. Configuration Schema Export

Pydantic can generate JSON Schema:
```python
schema = Settings.model_json_schema()
# Use for documentation, validation, etc.
```

### 2. Configuration Validation CLI

```bash
$ freya config validate config/default.yaml
✅ Configuration is valid

$ freya config validate config/invalid.yaml
❌ Configuration validation failed:
  - stt.sample_rate: Must be greater than 0
  - app.startup_mode: Must be 'normal' or 'diagnostic'
```

### 3. Configuration Migration Tool

```bash
$ freya config migrate config/old.yaml config/new.yaml
✅ Migrated configuration to new format
⚠️  Added default values for 3 new fields
```

## Recommendation

**Adopt `config_v2.py` as the primary configuration system.**

Benefits far outweigh migration effort:
- Immediate validation improvements
- Better developer experience
- Industry-standard approach
- Future-proof architecture

Migration can be done gradually without breaking existing code.

---

**Files Changed:**
- ✅ Created `freya/core/config_v2.py` (527 lines)
- ✅ Created `docs/CONFIGURATION_IMPROVEMENTS.md` (this file)

**Next Steps:**
1. Test config_v2 with existing YAML files
2. Update main.py to use config_v2
3. Update tests to use config_v2
4. Deprecate config.py
5. Remove config.py in future release
