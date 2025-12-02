"""Configuration loader for Freya using Pydantic for validation.

This module provides type-safe configuration loading with automatic validation
using Pydantic models. All configuration is validated at load time, failing fast
with clear error messages if the configuration is invalid.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator

from .logger import get_logger

logger = get_logger("config")


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""


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

    class Config:
        frozen = True


class ShortTermMemoryConfig(BaseModel):
    """Short-term conversation memory configuration.

    Attributes:
        max_history: Maximum number of messages to keep in memory
        enable_summarization: Enable automatic conversation summarization
        summary_trigger_ratio: Trigger summary when history reaches this ratio of max
        max_summaries: Maximum number of summaries to keep
    """

    max_history: int = Field(default=10, gt=0)
    enable_summarization: bool = Field(default=False)
    summary_trigger_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    max_summaries: int = Field(default=3, gt=0)

    class Config:
        frozen = True


class LongTermMemoryConfig(BaseModel):
    """Long-term semantic memory configuration.

    Attributes:
        enabled: Enable long-term memory storage
        store_type: Storage backend type (currently only 'chroma' supported)
        db_path: Path to database file
        recall_limit: Maximum number of memories to recall
        min_similarity: Minimum similarity score for memory retrieval (0.0-1.0)
        auto_store_keywords: Keywords that trigger automatic memory storage
        store_assistant_messages: Store assistant responses in long-term memory
    """

    enabled: bool = Field(default=False)
    store_type: str = Field(default="chroma")
    db_path: str = Field(default="~/.freya/memory")
    recall_limit: int = Field(default=3, gt=0)
    min_similarity: float = Field(default=0.15, ge=0.0, le=1.0)
    auto_store_keywords: tuple[str, ...] = Field(default_factory=tuple)
    store_assistant_messages: bool = Field(default=False)

    @field_validator("store_type")
    @classmethod
    def validate_store_type(cls, v: str) -> str:
        """Validate storage type is supported."""
        if v not in ["chroma", "sqlite"]:
            raise ValueError(f"store_type must be 'chroma' or 'sqlite', got '{v}'")
        return v

    class Config:
        frozen = True


class MemoryConfig(BaseModel):
    """Combined memory configuration.

    Attributes:
        short_term: Short-term conversation memory settings
        long_term: Long-term semantic memory settings
    """

    short_term: ShortTermMemoryConfig = Field(default_factory=ShortTermMemoryConfig)
    long_term: LongTermMemoryConfig = Field(default_factory=LongTermMemoryConfig)

    class Config:
        frozen = True


class AppConfig(BaseModel):
    """Application behavior configuration.

    Attributes:
        system_prompt: System prompt for LLM
        max_history: Maximum conversation history (mirrors short_term.max_history)
        wake_word: Wake word phrase (e.g., "Hey, Freya")
        wake_word_sensitivity: Wake word detection sensitivity (0.0-1.0)
        wake_session_seconds: Seconds to keep session active after wake word
        startup_mode: Startup mode ('normal' or 'diagnostic')
        prompt_for_mode: Prompt user to select mode at startup
        interaction_mode: Default interaction mode ('voice' or 'text')
        mode_toggle_hotkey: Hotkey to toggle between voice/text modes
    """

    system_prompt: str = Field(default="You are Freya, a helpful local AI assistant.")
    max_history: int = Field(default=10, gt=0)
    wake_word: str = Field(default="Hey, Freya", min_length=1)
    wake_word_sensitivity: float = Field(default=0.75, ge=0.0, le=1.0)
    wake_session_seconds: float = Field(default=8.0, ge=0.0)
    startup_mode: str = Field(default="normal")
    prompt_for_mode: bool = Field(default=True)
    interaction_mode: str = Field(default="voice")
    mode_toggle_hotkey: str = Field(default="ctrl+t")

    @field_validator("startup_mode")
    @classmethod
    def validate_startup_mode(cls, v: str) -> str:
        """Validate startup mode."""
        v = v.strip().lower()
        if v not in ["normal", "diagnostic"]:
            logger.warning("Invalid startup_mode '%s', defaulting to 'normal'", v)
            return "normal"
        return v

    @field_validator("interaction_mode")
    @classmethod
    def validate_interaction_mode(cls, v: str) -> str:
        """Validate interaction mode."""
        v = v.strip().lower()
        if v not in ["voice", "text"]:
            logger.warning("Invalid interaction_mode '%s', defaulting to 'voice'", v)
            return "voice"
        return v

    class Config:
        frozen = True


class SpeechToTextConfig(BaseModel):
    """Speech-to-text configuration using faster-whisper.

    Attributes:
        model: Whisper model name (e.g., 'base', 'small', 'medium')
        device: Device for inference ('auto', 'cpu', 'cuda')
        sample_rate: Audio sample rate in Hz
        silence_threshold: RMS threshold for silence detection (0.0-1.0)
        silence_duration: Seconds of silence before stopping recording
        max_record_seconds: Maximum recording duration in seconds
        prompt_tone_frequency: Frequency of recording prompt tone in Hz
        prompt_tone_duration: Duration of recording prompt tone in seconds
        prompt_tone_volume: Volume of recording prompt tone (0.0-1.0)
    """

    model: str = Field(default="base")
    device: str = Field(default="auto")
    sample_rate: int = Field(default=16000, gt=0)
    silence_threshold: float = Field(default=0.02, ge=0.0, le=1.0)
    silence_duration: float = Field(default=0.7, gt=0.0)
    max_record_seconds: float = Field(default=30.0, gt=0.0)
    prompt_tone_frequency: float = Field(default=880.0, gt=0.0)
    prompt_tone_duration: float = Field(default=0.2, gt=0.0)
    prompt_tone_volume: float = Field(default=0.2, ge=0.0, le=1.0)

    class Config:
        frozen = True


class WakeDetectorConfig(BaseModel):
    """Wake word detector configuration.

    Attributes:
        model: Whisper model for wake word detection (typically 'tiny')
        device: Device for inference ('auto', 'cpu', 'cuda')
        sample_rate: Audio sample rate in Hz
        chunk_seconds: Duration of each audio chunk for processing
    """

    model: str = Field(default="tiny")
    device: str = Field(default="cpu")
    sample_rate: int = Field(default=16000, gt=0)
    chunk_seconds: float = Field(default=2.0, gt=0.0)

    class Config:
        frozen = True


class ElevenLabsConfig(BaseModel):
    """ElevenLabs TTS API configuration.

    Attributes:
        api_key: ElevenLabs API key
        voice_id: Voice ID to use
        model: Model name (e.g., 'eleven_turbo_v2_5')
        stability: Voice stability parameter (0.0-1.0)
        similarity_boost: Similarity boost parameter (0.0-1.0)
        style: Style parameter (0.0-1.0)
        use_speaker_boost: Enable speaker boost
    """

    api_key: str = Field(default="")
    voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM")
    model: str = Field(default="eleven_turbo_v2_5")
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0)
    style: float = Field(default=0.0, ge=0.0, le=1.0)
    use_speaker_boost: bool = Field(default=True)

    class Config:
        frozen = True


class TextToSpeechConfig(BaseModel):
    """Text-to-speech configuration.

    Attributes:
        engine: TTS engine ('piper' or 'elevenlabs')
        voice_path: Path to Piper voice file (for Piper engine)
        preload_phrases: Phrases to pre-synthesize for faster playback
        elevenlabs: ElevenLabs API configuration
    """

    engine: str = Field(default="piper")
    voice_path: str = Field(default="voices/en_GB-southern_english_female-low.onnx")
    preload_phrases: tuple[str, ...] = Field(default_factory=tuple)
    elevenlabs: ElevenLabsConfig = Field(default_factory=ElevenLabsConfig)

    @field_validator("engine")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        """Validate TTS engine."""
        v = v.strip().lower()
        if v not in ["piper", "elevenlabs"]:
            raise ValueError(f"TTS engine must be 'piper' or 'elevenlabs', got '{v}'")
        return v

    class Config:
        frozen = True


class FaceRecognitionConfig(BaseModel):
    """Facial recognition configuration.

    Attributes:
        enabled: Enable facial recognition
        known_faces_dir: Directory containing known face images
        detection_model: Face detection model ('hog' or 'cnn')
        encoding_model: Face encoding model ('small' or 'large')
        tolerance: Face matching tolerance (0.0-1.0, lower is stricter)
        camera_channel: Camera channel identifier
        min_recognition_interval: Minimum seconds between recognizing same face
    """

    enabled: bool = Field(default=False)
    known_faces_dir: str = Field(default="data/faces")
    detection_model: str = Field(default="hog")
    encoding_model: str = Field(default="small")
    tolerance: float = Field(default=0.5, ge=0.0, le=1.0)
    camera_channel: Optional[str] = Field(default=None)
    min_recognition_interval: float = Field(default=5.0, ge=0.0)

    @field_validator("detection_model")
    @classmethod
    def validate_detection_model(cls, v: str) -> str:
        """Validate face detection model."""
        if v not in ["hog", "cnn"]:
            raise ValueError(f"detection_model must be 'hog' or 'cnn', got '{v}'")
        return v

    @field_validator("encoding_model")
    @classmethod
    def validate_encoding_model(cls, v: str) -> str:
        """Validate face encoding model."""
        if v not in ["small", "large"]:
            raise ValueError(f"encoding_model must be 'small' or 'large', got '{v}'")
        return v

    class Config:
        frozen = True


class VisionConfig(BaseModel):
    """Vision module configuration.

    Attributes:
        facial_recognition: Facial recognition settings
    """

    facial_recognition: FaceRecognitionConfig = Field(default_factory=FaceRecognitionConfig)

    class Config:
        frozen = True


class Settings(BaseModel):
    """Complete application settings.

    This is the root configuration model that contains all sub-configurations.
    All settings are validated at load time using Pydantic validators.

    Attributes:
        ollama: Ollama LLM configuration
        stt: Speech-to-text configuration
        tts: Text-to-speech configuration
        app: Application behavior configuration
        memory: Memory system configuration
        wake_detector: Wake word detector configuration
        vision: Vision system configuration
    """

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    stt: SpeechToTextConfig = Field(default_factory=SpeechToTextConfig)
    tts: TextToSpeechConfig = Field(default_factory=TextToSpeechConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    wake_detector: WakeDetectorConfig = Field(default_factory=WakeDetectorConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)

    @model_validator(mode="after")
    def sync_max_history(self) -> "Settings":
        """Sync app.max_history with memory.short_term.max_history."""
        # Ensure consistency between app and memory max_history
        if self.app.max_history != self.memory.short_term.max_history:
            logger.debug(
                "Syncing app.max_history (%d) with memory.short_term.max_history (%d)",
                self.app.max_history,
                self.memory.short_term.max_history,
            )
            # Update app to match memory (memory is source of truth)
            object.__setattr__(
                self,
                "app",
                self.app.model_copy(update={"max_history": self.memory.short_term.max_history}),
            )
        return self

    class Config:
        frozen = True


# Configuration file resolution
_DEFAULT_CONFIG_PATH = Path("config/default.yaml")
_ENV_VAR = "FREYA_CONFIG"


def _load_raw_config(path: Path) -> Dict[str, Any]:
    """Load raw YAML configuration from file.

    Args:
        path: Path to YAML configuration file

    Returns:
        Dictionary of raw configuration values

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    logger.debug("Loading configuration from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        try:
            config = yaml.safe_load(handle)
            return config or {}
        except yaml.YAMLError as exc:
            raise ConfigValidationError(f"Failed to parse YAML configuration: {exc}") from exc


def _resolve_config_path(path: Optional[Path]) -> Path:
    """Resolve configuration file path.

    Priority order:
    1. Explicit path parameter
    2. FREYA_CONFIG environment variable
    3. Default path (config/default.yaml)

    Args:
        path: Optional explicit path

    Returns:
        Resolved configuration path
    """
    if path:
        return path
    env_path = os.getenv(_ENV_VAR)
    if env_path:
        return Path(env_path)
    return _DEFAULT_CONFIG_PATH


def _apply_env_overrides(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to raw configuration.

    Environment variables take precedence over file configuration.

    Supported overrides:
    - OLLAMA_HOST: Overrides ollama.host
    - OLLAMA_MODEL: Overrides ollama.model
    - MEMORY_DB_PATH: Overrides memory.long_term.db_path
    - ELEVENLABS_API_KEY: Overrides tts.elevenlabs.api_key
    - ELEVENLABS_VOICE_ID: Overrides tts.elevenlabs.voice_id
    - ELEVENLABS_MODEL: Overrides tts.elevenlabs.model

    Args:
        raw: Raw configuration dictionary

    Returns:
        Configuration with environment variable overrides applied
    """
    # Ollama overrides
    if "OLLAMA_HOST" in os.environ:
        raw.setdefault("ollama", {})["host"] = os.environ["OLLAMA_HOST"]
    if "OLLAMA_MODEL" in os.environ:
        raw.setdefault("ollama", {})["model"] = os.environ["OLLAMA_MODEL"]

    # Memory overrides
    if "MEMORY_DB_PATH" in os.environ:
        raw.setdefault("memory", {}).setdefault("long_term", {})[
            "db_path"
        ] = os.environ["MEMORY_DB_PATH"]

    # ElevenLabs overrides
    if any(k in os.environ for k in ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "ELEVENLABS_MODEL"]):
        raw.setdefault("tts", {}).setdefault("elevenlabs", {})
        if "ELEVENLABS_API_KEY" in os.environ:
            raw["tts"]["elevenlabs"]["api_key"] = os.environ["ELEVENLABS_API_KEY"]
        if "ELEVENLABS_VOICE_ID" in os.environ:
            raw["tts"]["elevenlabs"]["voice_id"] = os.environ["ELEVENLABS_VOICE_ID"]
        if "ELEVENLABS_MODEL" in os.environ:
            raw["tts"]["elevenlabs"]["model"] = os.environ["ELEVENLABS_MODEL"]

    return raw


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load and validate application settings from YAML configuration.

    This function:
    1. Loads environment variables from .env file
    2. Resolves configuration file path
    3. Loads raw YAML configuration
    4. Applies environment variable overrides
    5. Validates configuration using Pydantic models
    6. Returns validated Settings object

    The configuration is fully validated at load time. If any validation
    fails, a clear error message is raised indicating the problem.

    Args:
        path: Optional path to configuration file. If not provided, uses
              FREYA_CONFIG environment variable or default path.

    Returns:
        Validated Settings object with all configuration

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ConfigValidationError: If configuration is invalid
        pydantic.ValidationError: If configuration fails Pydantic validation

    Example:
        >>> settings = load_settings()
        >>> print(settings.ollama.model)
        'llama3.2:3b'
        >>> print(settings.app.wake_word)
        'Hey, Freya'
    """
    # Load environment variables from .env file if present
    load_dotenv()

    # Resolve and load configuration file
    config_path = _resolve_config_path(path)
    raw = _load_raw_config(config_path)

    # Apply environment variable overrides
    raw = _apply_env_overrides(raw)

    # Validate and construct Settings object
    # Pydantic will automatically validate all fields and nested models
    try:
        settings = Settings(**raw)
        logger.info("Configuration loaded successfully from %s", config_path)
        logger.debug("Settings: %s", settings)
        return settings
    except Exception as exc:
        logger.error("Configuration validation failed: %s", exc)
        raise ConfigValidationError(f"Invalid configuration: {exc}") from exc


__all__ = [
    "Settings",
    "OllamaConfig",
    "AppConfig",
    "SpeechToTextConfig",
    "TextToSpeechConfig",
    "WakeDetectorConfig",
    "MemoryConfig",
    "ShortTermMemoryConfig",
    "LongTermMemoryConfig",
    "FaceRecognitionConfig",
    "VisionConfig",
    "ElevenLabsConfig",
    "ConfigValidationError",
    "load_settings",
]
