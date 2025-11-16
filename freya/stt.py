"""Speech-to-text utilities powered by faster-whisper."""

from __future__ import annotations

import queue
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

try:  # pragma: no cover - exercised via runtime import availability
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover - depends on optional dep
    sd = None  # type: ignore[assignment]
    _SOUNDDEVICE_ERROR = exc
else:  # pragma: no cover - passthrough
    _SOUNDDEVICE_ERROR = None

try:  # pragma: no cover - exercised via runtime import availability
    import soundfile as sf
except ImportError as exc:  # pragma: no cover - depends on optional dep
    sf = None  # type: ignore[assignment]
    _SOUNDFILE_ERROR = exc
else:  # pragma: no cover - passthrough
    _SOUNDFILE_ERROR = None

try:  # pragma: no cover - exercised via runtime import availability
    from faster_whisper import WhisperModel
except ImportError as exc:  # pragma: no cover - depends on optional dep
    WhisperModel = None  # type: ignore[assignment]
    _WHISPER_ERROR = exc
else:  # pragma: no cover - passthrough
    _WHISPER_ERROR = None

try:  # pragma: no cover - exercised via runtime import availability
    import ctranslate2  # type: ignore
except ImportError:  # pragma: no cover - optional but recommended for GPU detection
    ctranslate2 = None  # type: ignore[assignment]

from .config import SpeechToTextConfig
from .logger import get_logger

logger = get_logger("stt")


class SpeechToTextError(RuntimeError):
    """Raised when audio capture or transcription fails."""


@dataclass
class _RecordingResult:
    samples: np.ndarray
    samplerate: int


class SpeechToText:
    """Capture microphone audio and transcribe it using faster-whisper."""

    def __init__(self, config: SpeechToTextConfig) -> None:
        self._config = config
        self._ensure_dependencies()
        self._model, self._active_device = self._load_whisper_model(config)

    @property
    def device(self) -> str:
        """Return the device faster-whisper is currently using."""
        return self._active_device

    def _load_whisper_model(
        self, config: SpeechToTextConfig
    ) -> tuple["WhisperModel", str]:
        """Load faster-whisper on the requested device, falling back to CPU if needed."""
        if WhisperModel is None:  # pragma: no cover - handled in _ensure_dependencies
            raise SpeechToTextError("faster-whisper is not available")

        requested = (config.device or "").strip().lower()
        candidates: list[str] = []

        def _maybe_add(device: str) -> None:
            if device and device not in candidates:
                candidates.append(device)

        if requested in {"", "auto"}:
            if self._cuda_available():
                _maybe_add("cuda")
            _maybe_add("cpu")
        else:
            _maybe_add(requested)
            if requested != "cpu":
                _maybe_add("cpu")

        last_error: Optional[Exception] = None
        for device in candidates or ["cpu"]:
            if device.startswith("cuda") and not self._cuda_available():
                logger.warning(
                    "Skipping CUDA device '%s' because no compatible GPU was detected",
                    device,
                )
                continue

            compute_type = "int8_float16" if device.startswith("cuda") else "int8"

            try:
                logger.info(
                    "Loading faster-whisper model '%s' on device '%s'", config.model, device
                )
                model = WhisperModel(
                    config.model,
                    device=device,
                    compute_type=compute_type,
                )
            except Exception as exc:  # pragma: no cover - depends on runtime
                last_error = exc
                logger.warning(
                    "Failed to load faster-whisper model on device '%s': %s", device, exc
                )
                continue

            if requested not in {"", "auto", device}:
                logger.info(
                    "faster-whisper loaded on '%s' after falling back from requested '%s'",
                    device,
                    requested,
                )
            elif requested in {"", "auto"}:
                logger.info("faster-whisper device resolved to '%s'", device)
            return model, device

        message = "faster-whisper could not be initialised on any supported device"
        raise SpeechToTextError(message) from last_error

    def _cuda_available(self) -> bool:
        """Return True if a CUDA device appears to be available."""
        try:
            if ctranslate2 is not None and ctranslate2.get_device_count("cuda") > 0:
                return True
        except Exception:  # pragma: no cover - ctranslate2 probing errors
            logger.debug("ctranslate2 failed to enumerate CUDA devices", exc_info=True)

        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:  # pragma: no cover - torch optional
            return False

    def _ensure_dependencies(self) -> None:
        missing: list[str] = []
        if _SOUNDDEVICE_ERROR is not None:
            missing.append("sounddevice (pip install sounddevice)")
        if _SOUNDFILE_ERROR is not None:
            missing.append("soundfile (pip install soundfile)")
        if _WHISPER_ERROR is not None:
            missing.append("faster-whisper (pip install faster-whisper)")

        if missing:
            message = (
                "Speech input dependencies are not installed: "
                + ", ".join(missing)
                + ". Refer to the README 'Voice dependencies' section for setup instructions."
            )
            raise SpeechToTextError(message)

    def play_prompt_tone(self) -> None:
        """Play an audible tone signaling the start of recording."""
        duration = self._config.prompt_tone_duration
        if duration <= 0:
            return
        samplerate = self._config.sample_rate
        t = np.linspace(0, duration, int(samplerate * duration), False)
        tone = (
            self._config.prompt_tone_volume
            * np.sin(2 * np.pi * self._config.prompt_tone_frequency * t)
        ).astype(np.float32)
        logger.debug("Playing prompt tone for %.2f seconds", duration)
        try:
            sd.play(tone, samplerate)
            sd.wait()
        except Exception as exc:  # pragma: no cover - depends on audio device
            logger.exception("Failed to play prompt tone: %s", exc)
            raise SpeechToTextError("Unable to play the listening prompt tone") from exc

    def listen(self) -> str:
        """Record speech from the microphone and return a transcription."""
        try:
            recording = self._record_until_silence()
        except Exception as exc:  # pragma: no cover - depends on audio device
            logger.exception("Failed to record audio: %s", exc)
            raise SpeechToTextError("Could not access the microphone") from exc

        if recording.samples.size == 0:
            logger.warning("No audio samples captured")
            return ""

        if sf is None:  # pragma: no cover - handled by dependency check
            raise SpeechToTextError("soundfile is required to save temporary audio")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            temp_path = Path(handle.name)
            sf.write(handle, recording.samples, recording.samplerate)

        text = ""
        try:
            logger.debug("Transcribing audio with faster-whisper")
            segments, info = self._model.transcribe(
                str(temp_path),
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=True,
            )
            pieces = [segment.text.strip() for segment in segments if getattr(segment, "text", "")]
            text = " ".join(filter(None, pieces)).strip()
            if info.language:
                logger.debug("Detected language: %s (prob=%.3f)", info.language, info.language_probability)
        except Exception as exc:  # pragma: no cover - depends on whisper runtime
            logger.exception("faster-whisper transcription failed: %s", exc)
            raise SpeechToTextError("faster-whisper failed to transcribe the audio") from exc
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Failed to remove temporary audio file: %s", temp_path)

        text = text.strip()
        logger.info("Transcribed speech: %s", text)
        return text

    def _record_until_silence(self) -> _RecordingResult:
        """Capture audio until silence is detected or max duration is reached."""
        q: "queue.Queue[np.ndarray]" = queue.Queue()
        samplerate = self._config.sample_rate
        silence_threshold = self._config.silence_threshold
        silence_duration = self._config.silence_duration
        max_duration = self._config.max_record_seconds

        logger.debug(
            "Recording with sample rate %s, silence threshold %s", samplerate, silence_threshold
        )

        def _callback(indata: np.ndarray, frames: int, time_info, status) -> None:
            if status:
                logger.debug("Input stream status: %s", status)
            q.put(indata.copy())

        frames: list[np.ndarray] = []
        silence_start: Optional[float] = None
        start_time = time.time()

        with sd.InputStream(
            samplerate=samplerate,
            channels=1,
            dtype="float32",
            callback=_callback,
        ):
            while True:
                try:
                    data = q.get(timeout=1.0)
                except queue.Empty:
                    logger.debug("No audio frames received yet")
                    continue

                frames.append(data)
                rms = float(np.sqrt(np.mean(np.square(data))))
                if rms < silence_threshold:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= silence_duration:
                        logger.debug("Silence detected for %.2f seconds", silence_duration)
                        break
                else:
                    silence_start = None

                if time.time() - start_time >= max_duration:
                    logger.debug("Reached maximum recording duration: %s", max_duration)
                    break

        if not frames:
            return _RecordingResult(samples=np.array([], dtype=np.float32), samplerate=samplerate)

        audio = np.concatenate(frames, axis=0).astype(np.float32)
        logger.debug("Recorded %d samples", audio.size)
        return _RecordingResult(samples=audio, samplerate=samplerate)


__all__ = ["SpeechToText", "SpeechToTextError"]
