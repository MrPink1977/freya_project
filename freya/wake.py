"""Lightweight wake word detection powered by faster-whisper."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

try:  # pragma: no cover - exercised at runtime
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover - optional dependency
    sd = None  # type: ignore[assignment]
    _SOUNDDEVICE_ERROR = exc
else:  # pragma: no cover - passthrough
    _SOUNDDEVICE_ERROR = None

try:  # pragma: no cover - exercised at runtime
    from faster_whisper import WhisperModel
except ImportError as exc:  # pragma: no cover - optional dependency
    WhisperModel = None  # type: ignore[assignment]
    _WHISPER_ERROR = exc
else:  # pragma: no cover - passthrough
    _WHISPER_ERROR = None

try:  # pragma: no cover - optional dependency for CUDA checks
    import ctranslate2  # type: ignore
except ImportError:  # pragma: no cover - dependency bundled with faster-whisper
    ctranslate2 = None  # type: ignore[assignment]

from .config import WakeDetectorConfig
from .logger import get_logger

logger = get_logger("wake")


class WakeWordDetectorError(RuntimeError):
    """Raised when the wake word detector cannot initialise or record audio."""


class WakeWordDetector:
    """Capture short audio windows and transcribe them with faster-whisper tiny."""

    def __init__(self, config: WakeDetectorConfig) -> None:
        self._config = config
        self._ensure_dependencies()
        self._model, self._active_device = self._load_model(config)
        self._sample_rate = max(1, int(config.sample_rate))
        self._chunk_seconds = max(0.25, float(config.chunk_seconds))
        self._chunk_frames = max(1, int(self._sample_rate * self._chunk_seconds))
        logger.info(
            "Wake detector using faster-whisper model '%s' on device '%s'",
            config.model,
            self._active_device,
        )

    def _ensure_dependencies(self) -> None:
        missing = []
        if _SOUNDDEVICE_ERROR is not None:
            missing.append(f"sounddevice ({_SOUNDDEVICE_ERROR})")
        if _WHISPER_ERROR is not None:
            missing.append(f"faster-whisper ({_WHISPER_ERROR})")
        if missing:
            raise WakeWordDetectorError(
                "Wake word detector dependencies missing: " + ", ".join(missing)
            )

    def _load_model(self, config: WakeDetectorConfig) -> Tuple["WhisperModel", str]:
        if WhisperModel is None:  # pragma: no cover - handled via dependency check
            raise WakeWordDetectorError("faster-whisper is not available")

        requested = (config.device or "cpu").strip().lower()
        candidates: list[str] = []

        def _add(device: str) -> None:
            if device and device not in candidates:
                candidates.append(device)

        if requested in {"", "auto"}:
            if self._cuda_available():
                _add("cuda")
            _add("cpu")
        else:
            _add(requested)
            if requested != "cpu":
                _add("cpu")

        last_error: Optional[Exception] = None
        for device in candidates or ["cpu"]:
            if device.startswith("cuda") and not self._cuda_available():
                logger.debug("CUDA device '%s' unavailable for wake detector", device)
                continue
            compute_type = "int8_float16" if device.startswith("cuda") else "int8"
            try:
                model = WhisperModel(
                    config.model,
                    device=device,
                    compute_type=compute_type,
                )
            except Exception as exc:  # pragma: no cover - backend dependent
                last_error = exc
                logger.debug("Failed to load wake detector model on '%s': %s", device, exc)
                continue
            if device != requested and requested not in {"", "auto", device}:
                logger.info(
                    "Wake detector fell back to device '%s' (requested '%s')",
                    device,
                    requested,
                )
            elif requested in {"", "auto"}:
                logger.debug("Wake detector resolved device '%s'", device)
            return model, device

        message = "Wake detector could not initialise faster-whisper on any device"
        raise WakeWordDetectorError(message) from last_error

    def _cuda_available(self) -> bool:
        try:
            if ctranslate2 is not None and ctranslate2.get_device_count("cuda") > 0:
                return True
        except Exception:  # pragma: no cover - device probing errors
            logger.debug("Wake detector CUDA probe failed", exc_info=True)

        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:  # pragma: no cover - torch optional
            return False

    def listen_once(self) -> str:
        """Record a short audio window and return the transcript."""
        if sd is None:  # pragma: no cover - handled via dependency check
            raise WakeWordDetectorError("sounddevice is unavailable")

        try:
            recording = sd.rec(
                self._chunk_frames,
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocking=True,
            )
        except Exception as exc:  # pragma: no cover - hardware specific
            logger.exception("Wake detector failed to capture audio: %s", exc)
            raise WakeWordDetectorError("Wake detector could not access the microphone") from exc

        audio = np.asarray(recording, dtype=np.float32).flatten()
        if audio.size == 0:
            return ""

        text = ""
        try:
            segments, _info = self._model.transcribe(
                audio,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                language="en",
                vad_filter=False,
                condition_on_previous_text=False,
            )
            text = " ".join(
                filter(
                    None,
                    (segment.text.strip() for segment in segments if getattr(segment, "text", "")),
                )
            ).strip()
        except Exception as exc:  # pragma: no cover - backend dependent
            logger.exception("Wake detector transcription failed: %s", exc)
            raise WakeWordDetectorError("Wake detector failed to transcribe audio") from exc

        if text:
            logger.debug("Wake detector transcript: %s", text)
        return text

    def close(self) -> None:
        """Release references to the underlying faster-whisper model.

        Note: WhisperModel doesn't provide an explicit cleanup method, so we
        release the reference and rely on Python's garbage collector to free
        the underlying resources.
        """
        if hasattr(self, "_model"):
            self._model = None  # type: ignore[assignment]


__all__ = ["WakeWordDetector", "WakeWordDetectorError"]
