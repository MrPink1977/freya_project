"""Configuration loader for Freya."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import yaml

from .logger import get_logger

logger = get_logger("config")


def _load_env_file() -> None:
    """Load environment variables from .env file if it exists."""
    env_path = Path(".env")
    if not env_path.exists():
        return

    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already in environment
                    if key and not os.getenv(key):
                        os.environ[key] = value
        logger.debug("Loaded environment variables from .env file")
    except Exception as exc:
        logger.warning("Failed to load .env file: %s", exc)


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""


def _validate_range(
    value: float,
    min_val: float,
    max_val: float,
    field_name: str,
    section: str = "",
) -> None:
    """Validate that a numeric value is within the expected range."""
    prefix = f"{section}." if section else ""
    if not (min_val <= value <= max_val):
        raise ConfigValidationError(
            f"Configuration error: {prefix}{field_name} must be between {min_val} and {max_val}, "
            f"got {value}"
        )


def _validate_positive(value: float, field_name: str, section: str = "") -> None:
    """Validate that a numeric value is positive."""
    prefix = f"{section}." if section else ""
    if value <= 0:
        raise ConfigValidationError(
            f"Configuration error: {prefix}{field_name} must be positive, got {value}"
        )


def _validate_non_empty(value: str, field_name: str, section: str = "") -> None:
    """Validate that a string value is not empty."""
    prefix = f"{section}." if section else ""
    if not value or not value.strip():
        raise ConfigValidationError(
            f"Configuration error: {prefix}{field_name} cannot be empty"
        )


def _validate_choice(
    value: str, choices: Sequence[str], field_name: str, section: str = ""
) -> None:
    """Validate that a value is one of the allowed choices."""
    prefix = f"{section}." if section else ""
    if value not in choices:
        choices_str = ", ".join(f"'{c}'" for c in choices)
        raise ConfigValidationError(
            f"Configuration error: {prefix}{field_name} must be one of {choices_str}, "
            f"got '{value}'"
        )


@dataclass(frozen=True)
class OllamaConfig:
    host: str
    model: str
    options: Dict[str, Any]


@dataclass(frozen=True)
class AppConfig:
    system_prompt: str
    max_history: int
    wake_word: str
    wake_word_sensitivity: float
    wake_session_seconds: float
    startup_mode: str
    prompt_for_mode: bool
    interaction_mode: str
    mode_toggle_hotkey: str


@dataclass(frozen=True)
class WakeDetectorConfig:
    model: str
    device: str
    sample_rate: int
    chunk_seconds: float


@dataclass(frozen=True)
class ShortTermMemoryConfig:
    max_history: int
    enable_summarization: bool
    summary_trigger_ratio: float
    max_summaries: int


@dataclass(frozen=True)
class LongTermMemoryConfig:
    enabled: bool
    store_type: str
    db_path: str
    recall_limit: int
    min_similarity: float
    auto_store_keywords: Tuple[str, ...]
    store_assistant_messages: bool
    embedding_model: str = "all-MiniLM-L6-v2"  # Fast, lightweight, 384-dim embeddings


@dataclass(frozen=True)
class MemoryConfig:
    short_term: ShortTermMemoryConfig
    long_term: LongTermMemoryConfig


@dataclass(frozen=True)
class SpeechToTextConfig:
    model: str
    device: str
    sample_rate: int
    silence_threshold: float
    silence_duration: float
    max_record_seconds: float
    prompt_tone_frequency: float
    prompt_tone_duration: float
    prompt_tone_volume: float


@dataclass(frozen=True)
class ElevenLabsConfig:
    api_key: str
    voice_id: str
    model: str
    stability: float
    similarity_boost: float
    style: float
    use_speaker_boost: bool


@dataclass(frozen=True)
class TextToSpeechConfig:
    engine: str  # "piper" or "elevenlabs"
    voice_path: str
    preload_phrases: Tuple[str, ...]
    elevenlabs: ElevenLabsConfig


@dataclass(frozen=True)
class FaceRecognitionConfig:
    enabled: bool
    known_faces_dir: str
    detection_model: str
    encoding_model: str
    tolerance: float
    camera_channel: Optional[str]
    min_recognition_interval: float


@dataclass(frozen=True)
class VisionConfig:
    facial_recognition: FaceRecognitionConfig


@dataclass(frozen=True)
class Settings:
    ollama: OllamaConfig
    stt: SpeechToTextConfig
    tts: TextToSpeechConfig
    app: AppConfig
    memory: MemoryConfig
    wake_detector: WakeDetectorConfig
    vision: VisionConfig


_DEFAULT_CONFIG_PATH = Path("config/default.yaml")
_ENV_VAR = "FREYA_CONFIG"


def _load_raw_config(path: Path) -> Dict[str, Any]:
    logger.debug("Loading configuration from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _resolve_config_path(path: Optional[Path]) -> Path:
    if path:
        return path
    env_path = os.getenv(_ENV_VAR)
    if env_path:
        return Path(env_path)
    return _DEFAULT_CONFIG_PATH


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load application settings from YAML configuration."""
    # Load environment variables from .env file if present
    _load_env_file()

    config_path = _resolve_config_path(path)
    raw = _load_raw_config(config_path)

    ollama_raw = raw.get("ollama", {})
    app_raw = raw.get("app", {})
    stt_raw = raw.get("stt", {})
    wake_detector_raw = raw.get("wake_detector", {})
    vision_raw = raw.get("vision", {})
    tts_raw = raw.get("tts", {})
    memory_raw = raw.get("memory", {})

    # Validate Ollama configuration
    ollama_host = ollama_raw.get("host", "http://localhost:11434")
    ollama_model = ollama_raw.get("model", "llama3.2:3b")
    _validate_non_empty(ollama_host, "host", "ollama")
    _validate_non_empty(ollama_model, "model", "ollama")

    ollama_config = OllamaConfig(
        host=ollama_host,
        model=ollama_model,
        options=ollama_raw.get("options", {}),
    )
    default_history = int(app_raw.get("max_history", 10))
    _validate_positive(default_history, "max_history", "app")

    # Validate short-term memory configuration
    short_term_raw = memory_raw.get("short_term", {})
    st_max_history = int(short_term_raw.get("max_history", default_history))
    st_summary_ratio = float(short_term_raw.get("summary_trigger_ratio", 0.8))
    st_max_summaries = int(short_term_raw.get("max_summaries", 3))

    _validate_positive(st_max_history, "max_history", "memory.short_term")
    _validate_range(st_summary_ratio, 0.0, 1.0, "summary_trigger_ratio", "memory.short_term")
    _validate_positive(st_max_summaries, "max_summaries", "memory.short_term")

    short_term_config = ShortTermMemoryConfig(
        max_history=st_max_history,
        enable_summarization=bool(short_term_raw.get("enable_summarization", False)),
        summary_trigger_ratio=st_summary_ratio,
        max_summaries=st_max_summaries,
    )

    long_term_raw = memory_raw.get("long_term", {})
    keywords_raw: Sequence[Any] | str | None = long_term_raw.get("auto_store_keywords", ())
    if isinstance(keywords_raw, str):
        keywords_iterable: Sequence[Any] = (keywords_raw,)
    elif isinstance(keywords_raw, Sequence):
        keywords_iterable = keywords_raw
    else:
        keywords_iterable = ()
    auto_store_keywords: Tuple[str, ...] = tuple(
        str(keyword).strip().lower()
        for keyword in keywords_iterable
        if isinstance(keyword, (str, bytes)) and str(keyword).strip()
    )

    # Validate long-term memory configuration
    lt_recall_limit = int(long_term_raw.get("recall_limit", 3))
    lt_min_similarity = float(long_term_raw.get("min_similarity", 0.15))
    lt_store_type = str(long_term_raw.get("store_type", "sqlite"))

    _validate_positive(lt_recall_limit, "recall_limit", "memory.long_term")
    _validate_range(lt_min_similarity, 0.0, 1.0, "min_similarity", "memory.long_term")
    _validate_choice(lt_store_type, ["sqlite"], "store_type", "memory.long_term")

    long_term_config = LongTermMemoryConfig(
        enabled=bool(long_term_raw.get("enabled", False)),
        store_type=lt_store_type,
        db_path=str(long_term_raw.get("db_path", "freya_memory.db")),
        recall_limit=lt_recall_limit,
        min_similarity=lt_min_similarity,
        auto_store_keywords=auto_store_keywords,
        store_assistant_messages=bool(long_term_raw.get("store_assistant_messages", False)),
        embedding_model=str(long_term_raw.get("embedding_model", "all-MiniLM-L6-v2")),
    )

    memory_config = MemoryConfig(
        short_term=short_term_config,
        long_term=long_term_config,
    )

    # Validate app configuration
    startup_mode_raw = str(app_raw.get("startup_mode", "normal")).strip().lower()
    if startup_mode_raw not in {"normal", "diagnostic"}:
        logger.warning(
            "Invalid startup_mode '%s', defaulting to 'normal'", startup_mode_raw
        )
        startup_mode_raw = "normal"

    interaction_mode_raw = str(app_raw.get("interaction_mode", "voice")).strip().lower()
    if interaction_mode_raw not in {"voice", "text"}:
        logger.warning(
            "Invalid interaction_mode '%s', defaulting to 'voice'", interaction_mode_raw
        )
        interaction_mode_raw = "voice"

    toggle_hotkey = str(app_raw.get("mode_toggle_hotkey", "ctrl+t")).strip()
    wake_word = str(app_raw.get("wake_word", "Hey, Freya"))
    wake_sensitivity = float(app_raw.get("wake_word_sensitivity", 0.75))
    wake_session = float(app_raw.get("wake_session_seconds", 8.0))

    _validate_non_empty(wake_word, "wake_word", "app")
    _validate_range(wake_sensitivity, 0.0, 1.0, "wake_word_sensitivity", "app")
    if wake_session < 0:
        raise ConfigValidationError(
            f"Configuration error: app.wake_session_seconds cannot be negative, got {wake_session}"
        )

    app_config = AppConfig(
        system_prompt=app_raw.get(
            "system_prompt", "You are Freya, a helpful local AI assistant."
        ),
        max_history=memory_config.short_term.max_history,
        wake_word=wake_word,
        wake_word_sensitivity=wake_sensitivity,
        wake_session_seconds=wake_session,
        startup_mode=startup_mode_raw,
        prompt_for_mode=bool(app_raw.get("prompt_for_mode", True)),
        interaction_mode=interaction_mode_raw,
        mode_toggle_hotkey=toggle_hotkey,
    )
    # Validate STT configuration
    stt_device = stt_raw.get("device", "auto")
    if not stt_device:
        stt_device = "auto"

    stt_sample_rate = int(stt_raw.get("sample_rate", 16000))
    stt_silence_threshold = float(stt_raw.get("silence_threshold", 0.02))
    stt_silence_duration = float(stt_raw.get("silence_duration", 0.7))
    stt_max_record = float(stt_raw.get("max_record_seconds", 30))
    stt_tone_volume = float(stt_raw.get("prompt_tone_volume", 0.2))

    _validate_positive(stt_sample_rate, "sample_rate", "stt")
    _validate_range(stt_silence_threshold, 0.0, 1.0, "silence_threshold", "stt")
    _validate_positive(stt_silence_duration, "silence_duration", "stt")
    _validate_positive(stt_max_record, "max_record_seconds", "stt")
    _validate_range(stt_tone_volume, 0.0, 1.0, "prompt_tone_volume", "stt")

    stt_config = SpeechToTextConfig(
        model=stt_raw.get("model", "base"),
        device=str(stt_device),
        sample_rate=stt_sample_rate,
        silence_threshold=stt_silence_threshold,
        silence_duration=stt_silence_duration,
        max_record_seconds=stt_max_record,
        prompt_tone_frequency=float(stt_raw.get("prompt_tone_frequency", 880)),
        prompt_tone_duration=float(stt_raw.get("prompt_tone_duration", 0.2)),
        prompt_tone_volume=stt_tone_volume,
    )

    # Validate wake detector configuration
    wake_sample_rate = int(wake_detector_raw.get("sample_rate", stt_config.sample_rate))
    wake_chunk_seconds = float(wake_detector_raw.get("chunk_seconds", 2.0))

    _validate_positive(wake_sample_rate, "sample_rate", "wake_detector")
    _validate_positive(wake_chunk_seconds, "chunk_seconds", "wake_detector")

    wake_detector_config = WakeDetectorConfig(
        model=str(wake_detector_raw.get("model", "tiny")),
        device=str(wake_detector_raw.get("device", "cpu")),
        sample_rate=wake_sample_rate,
        chunk_seconds=wake_chunk_seconds,
    )
    face_raw = vision_raw.get("facial_recognition", {})
    camera_channel_raw = face_raw.get("camera_channel")
    if isinstance(camera_channel_raw, (str, bytes)):
        camera_channel_value = str(camera_channel_raw).strip()
        camera_channel = camera_channel_value or None
    else:
        camera_channel = None

    face_config = FaceRecognitionConfig(
        enabled=bool(face_raw.get("enabled", False)),
        known_faces_dir=str(face_raw.get("known_faces_dir", "data/faces")),
        detection_model=str(face_raw.get("detection_model", "hog")),
        encoding_model=str(face_raw.get("encoding_model", "small")),
        tolerance=float(face_raw.get("tolerance", 0.5)),
        camera_channel=camera_channel,
        min_recognition_interval=float(
            face_raw.get("min_recognition_interval", 5.0)
        ),
    )
    vision_config = VisionConfig(facial_recognition=face_config)

    # Parse TTS configuration
    tts_engine = str(tts_raw.get("engine", "piper")).lower()
    voice_path = tts_raw.get("voice_path", "voices/en_GB-southern_english_female-low.onnx")
    preload_raw = tts_raw.get("preload_phrases", ())
    if isinstance(preload_raw, str):
        preload_iterable: Sequence[Any] = (preload_raw,)
    elif isinstance(preload_raw, Sequence):
        preload_iterable = preload_raw
    else:
        preload_iterable = ()

    preload_phrases: Tuple[str, ...] = tuple(
        str(phrase).strip()
        for phrase in preload_iterable
        if isinstance(phrase, (str, bytes)) and str(phrase).strip()
    )

    # Parse ElevenLabs configuration (environment variables take precedence)
    elevenlabs_raw = tts_raw.get("elevenlabs", {})
    elevenlabs_config = ElevenLabsConfig(
        api_key=str(
            os.getenv("ELEVENLABS_API_KEY")
            or elevenlabs_raw.get("api_key", "")
        ),
        voice_id=str(
            os.getenv("ELEVENLABS_VOICE_ID")
            or elevenlabs_raw.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        ),
        model=str(
            os.getenv("ELEVENLABS_MODEL")
            or elevenlabs_raw.get("model", "eleven_turbo_v2_5")
        ),
        stability=float(elevenlabs_raw.get("stability", 0.5)),
        similarity_boost=float(elevenlabs_raw.get("similarity_boost", 0.75)),
        style=float(elevenlabs_raw.get("style", 0.0)),
        use_speaker_boost=bool(elevenlabs_raw.get("use_speaker_boost", True)),
    )

    tts_config = TextToSpeechConfig(
        engine=tts_engine,
        voice_path=str(voice_path),
        preload_phrases=preload_phrases,
        elevenlabs=elevenlabs_config,
    )

    settings = Settings(
        ollama=ollama_config,
        stt=stt_config,
        tts=tts_config,
        app=app_config,
        memory=memory_config,
        wake_detector=wake_detector_config,
        vision=vision_config,
    )
    logger.debug("Loaded settings: %s", settings)
    return settings
