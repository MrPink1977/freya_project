"""Configuration loader for Freya."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple
import os

import yaml

from .logger import get_logger

logger = get_logger("config")


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
class TextToSpeechConfig:
    voice_path: str
    preload_phrases: Tuple[str, ...]


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
    config_path = _resolve_config_path(path)
    raw = _load_raw_config(config_path)

    ollama_raw = raw.get("ollama", {})
    app_raw = raw.get("app", {})
    stt_raw = raw.get("stt", {})
    wake_detector_raw = raw.get("wake_detector", {})
    vision_raw = raw.get("vision", {})
    tts_raw = raw.get("tts", {})
    memory_raw = raw.get("memory", {})

    ollama_config = OllamaConfig(
        host=ollama_raw.get("host", "http://localhost:11434"),
        model=ollama_raw.get("model", "llama3.2:3b"),
        options=ollama_raw.get("options", {}),
    )
    default_history = int(app_raw.get("max_history", 10))

    short_term_raw = memory_raw.get("short_term", {})
    short_term_config = ShortTermMemoryConfig(
        max_history=int(short_term_raw.get("max_history", default_history)),
        enable_summarization=bool(short_term_raw.get("enable_summarization", False)),
        summary_trigger_ratio=float(short_term_raw.get("summary_trigger_ratio", 0.8)),
        max_summaries=int(short_term_raw.get("max_summaries", 3)),
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

    long_term_config = LongTermMemoryConfig(
        enabled=bool(long_term_raw.get("enabled", False)),
        store_type=str(long_term_raw.get("store_type", "sqlite")),
        db_path=str(long_term_raw.get("db_path", "freya_memory.db")),
        recall_limit=int(long_term_raw.get("recall_limit", 3)),
        min_similarity=float(long_term_raw.get("min_similarity", 0.15)),
        auto_store_keywords=auto_store_keywords,
        store_assistant_messages=bool(long_term_raw.get("store_assistant_messages", False)),
    )

    memory_config = MemoryConfig(
        short_term=short_term_config,
        long_term=long_term_config,
    )

    startup_mode_raw = str(app_raw.get("startup_mode", "normal")).strip().lower()
    if startup_mode_raw not in {"normal", "diagnostic"}:
        startup_mode_raw = "normal"

    interaction_mode_raw = str(app_raw.get("interaction_mode", "voice")).strip().lower()
    if interaction_mode_raw not in {"voice", "text"}:
        interaction_mode_raw = "voice"

    toggle_hotkey = str(app_raw.get("mode_toggle_hotkey", "ctrl+t")).strip()

    app_config = AppConfig(
        system_prompt=app_raw.get(
            "system_prompt", "You are Freya, a helpful local AI assistant."
        ),
        max_history=memory_config.short_term.max_history,
        wake_word=str(app_raw.get("wake_word", "Hey, Freya")),
        wake_word_sensitivity=float(app_raw.get("wake_word_sensitivity", 0.75)),
        wake_session_seconds=float(app_raw.get("wake_session_seconds", 8.0)),
        startup_mode=startup_mode_raw,
        prompt_for_mode=bool(app_raw.get("prompt_for_mode", True)),
        interaction_mode=interaction_mode_raw,
        mode_toggle_hotkey=toggle_hotkey,
    )
    stt_device = stt_raw.get("device", "auto")
    if not stt_device:
        stt_device = "auto"

    stt_config = SpeechToTextConfig(
        model=stt_raw.get("model", "base"),
        device=str(stt_device),
        sample_rate=int(stt_raw.get("sample_rate", 16000)),
        silence_threshold=float(stt_raw.get("silence_threshold", 0.02)),
        silence_duration=float(stt_raw.get("silence_duration", 0.7)),
        max_record_seconds=float(stt_raw.get("max_record_seconds", 30)),
        prompt_tone_frequency=float(stt_raw.get("prompt_tone_frequency", 880)),
        prompt_tone_duration=float(stt_raw.get("prompt_tone_duration", 0.2)),
        prompt_tone_volume=float(stt_raw.get("prompt_tone_volume", 0.2)),
    )
    wake_detector_config = WakeDetectorConfig(
        model=str(wake_detector_raw.get("model", "tiny")),
        device=str(wake_detector_raw.get("device", "cpu")),
        sample_rate=int(
            wake_detector_raw.get("sample_rate", stt_config.sample_rate)
        ),
        chunk_seconds=float(wake_detector_raw.get("chunk_seconds", 2.0)),
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

    tts_config = TextToSpeechConfig(
        voice_path=str(voice_path),
        preload_phrases=preload_phrases,
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