"""Text-to-speech utilities powered by Piper."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import threading
import wave
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

try:  # pragma: no cover - exercised via runtime import availability
    from piper import PiperVoice

    try:
        from piper.voice import AudioChunk  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - AudioChunk is optional in older builds
        AudioChunk = None  # type: ignore[assignment]
except ImportError as exc:  # pragma: no cover - depends on optional dep
    PiperVoice = None  # type: ignore[assignment]
    _PIPER_ERROR = exc
else:  # pragma: no cover - passthrough
    _PIPER_ERROR = None
    if "AudioChunk" not in globals():  # pragma: no cover - for mypy
        AudioChunk = None  # type: ignore[assignment]

try:  # pragma: no cover - exercised via runtime import availability
    import pyaudio
except ImportError as exc:  # pragma: no cover - depends on optional dep
    pyaudio = None  # type: ignore[assignment]
    _PYAUDIO_ERROR = exc
else:  # pragma: no cover - passthrough
    _PYAUDIO_ERROR = None

try:  # pragma: no cover - optional helper for Piper array outputs
    import numpy as np
except Exception:  # pragma: no cover - numpy ships with piper but guard regardless
    np = None  # type: ignore[assignment]

from .config import TextToSpeechConfig
from .logger import get_logger

logger = get_logger("tts")


class TextToSpeechError(RuntimeError):
    """Raised when synthesising or playing speech fails."""


class TextToSpeech:
    """Convert text responses into spoken audio output using Piper."""

    def __init__(self, config: TextToSpeechConfig) -> None:
        self._config = config
        self._stop_speech = threading.Event()

        if _PIPER_ERROR is not None:
            raise TextToSpeechError(
                "Text-to-speech dependency missing: piper-tts (pip install piper-tts)."
            ) from _PIPER_ERROR
        if _PYAUDIO_ERROR is not None:
            raise TextToSpeechError(
                "Audio playback dependency missing: pyaudio (pip install pyaudio)."
            ) from _PYAUDIO_ERROR

        voice_path = Path(config.voice_path).expanduser()
        if not voice_path.exists():
            raise TextToSpeechError(f"Voice file not found: {voice_path}")

        try:
            logger.info("Loading Piper voice from %s", voice_path)
            self._voice = PiperVoice.load(str(voice_path))
        except Exception as exc:  # pragma: no cover - depends on voice file integrity
            logger.exception("Failed to initialise Piper voice: %s", exc)
            raise TextToSpeechError("Could not initialise the Piper voice") from exc

        self._sample_rate = self._resolve_sample_rate(voice_path)
        logger.debug("Using Piper sample rate: %sHz", self._sample_rate)

        self._preloaded_audio: dict[str, tuple[bytes, ...]] = {}
        self._preload_common_phrases(config.preload_phrases)

    def speak(self, text: str) -> None:
        """Synthesize and play the provided text."""
        if not text or not text.strip():
            logger.debug("No text provided for speech output")
            return

        # Clear stop flag at start of new speech
        self._stop_speech.clear()

        trimmed = text.strip()
        logger.info("Speaking response: %s", trimmed[:1000])

        cached_chunks = self._preloaded_audio.get(trimmed)
        if cached_chunks is not None:
            chunk_iterable: Iterable[bytes] = cached_chunks
        else:
            try:
                chunk_iterable = self._generate_pcm_stream(trimmed)
            except TextToSpeechError:
                raise
            except Exception as exc:  # pragma: no cover - backend dependent
                logger.exception("Failed to synthesise speech: %s", exc)
                raise TextToSpeechError("Failed to synthesise speech output") from exc

        try:
            self._stream_pcm_chunks(chunk_iterable)
        except TextToSpeechError:
            raise
        except Exception as exc:  # pragma: no cover - depends on audio backend
            logger.exception("Failed to play audio: %s", exc)
            raise TextToSpeechError("Failed to play the synthesised audio") from exc

    def stop_speaking(self) -> None:
        """Signal the TTS to stop current playback."""
        self._stop_speech.set()
        logger.debug("Stop speech signal set")

    def preload_phrase(self, text: str) -> None:
        """Generate and cache speech audio for the provided phrase."""
        normalized = (text or "").strip()
        if not normalized or normalized in self._preloaded_audio:
            return

        try:
            chunks = tuple(self._generate_pcm_stream(normalized))
        except Exception as exc:  # pragma: no cover - backend dependent
            logger.debug("Failed to preload phrase '%s': %s", normalized, exc)
            return

        if not chunks:
            logger.debug("Piper returned no audio while preloading phrase '%s'", normalized)
            return

        self._preloaded_audio[normalized] = chunks
        logger.debug("Cached %d audio chunk(s) for phrase '%s'", len(chunks), normalized)

    def _preload_common_phrases(self, phrases: Sequence[str]) -> None:
        """Pre-synthesise frequently used phrases for instant playback."""
        if not phrases:
            return

        for phrase in phrases:
            normalized = (phrase or "").strip()
            if not normalized or normalized in self._preloaded_audio:
                continue
            try:
                chunks = tuple(self._generate_pcm_stream(normalized))
            except Exception as exc:  # pragma: no cover - backend dependent
                logger.debug("Skipping preload for phrase '%s' due to error: %s", normalized, exc)
                continue

            if not chunks:
                logger.debug(
                    "Skipping preload for phrase '%s' because no audio was produced",
                    normalized,
                )
                continue

            self._preloaded_audio[normalized] = chunks
            logger.debug("Preloaded %d audio chunk(s) for phrase '%s'", len(chunks), normalized)

    def _generate_pcm_stream(self, text: str) -> Iterable[bytes]:
        """Yield normalised PCM chunks for the given text."""
        try:
            result = self._voice.synthesize(text)
        except TypeError:
            # Older Piper builds require an explicit output handle/path.
            logger.debug("Piper synth requires explicit output handle; using temp file")
            pcm_bytes = self._synthesise_via_tempfile(text)
            if pcm_bytes:
                return (pcm_bytes,)
            return ()

        # Direct call succeeded. The return type varies between Piper versions.
        if isinstance(result, (bytes, bytearray, memoryview)):
            return (self._normalise_audio_block(result),)

        if isinstance(result, tuple) and result:
            # Some builds return (chunks, sample_rate)
            chunks = result[0]
            if len(result) > 1 and result[1]:
                self._maybe_update_sample_rate(result[1])
            return self._iter_normalised_chunks(chunks)

        if hasattr(result, "read"):
            # File-like object with WAV data.
            data = result.read()
            pcm_bytes = self._extract_pcm(data)
            return (pcm_bytes,) if pcm_bytes else ()

        if isinstance(result, (list, tuple)) or isinstance(result, Iterator):
            return self._iter_normalised_chunks(result)

        if isinstance(result, Iterable):
            return self._iter_normalised_chunks(result)

        logger.debug("Unknown Piper synth return type %r; using temp file fallback", type(result))
        pcm_bytes = self._synthesise_via_tempfile(text)
        if pcm_bytes:
            return (pcm_bytes,)
        return ()

    def _synthesise_via_tempfile(self, text: str) -> bytes:
        """Use a temporary WAV file for Piper builds lacking stream support."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = Path(tmp.name)

        try:
            try:
                # Preferred: Piper accepts a filesystem path directly.
                self._voice.synthesize(text, str(tmp_path))
            except TypeError:
                with tmp_path.open("wb") as handle:
                    self._voice.synthesize(text, handle)

            with tmp_path.open("rb") as handle:
                audio_bytes = handle.read()
        finally:
            with contextlib.suppress(FileNotFoundError):
                tmp_path.unlink()

        return self._extract_pcm(audio_bytes)

    def _iter_normalised_chunks(self, chunks: Iterable[object]) -> Iterator[bytes]:
        """Yield normalised 16-bit PCM chunks from Piper iterables."""
        for chunk in chunks:
            if chunk is None:
                continue

            if AudioChunk is not None and isinstance(chunk, AudioChunk):
                extractor = getattr(self, "_extract_audio_chunk", None)
                if callable(extractor):
                    payload = extractor(chunk)
                else:
                    logger.debug("AudioChunk extractor unavailable; falling back to generic payload resolution")
                    payload = self._resolve_chunk_payload(chunk)
            else:
                payload = self._resolve_chunk_payload(chunk)

            if payload is None:
                logger.warning(
                    "Skipping unexpected Piper chunk %s; summary=%s",
                    type(chunk).__name__,
                    self._describe_chunk(chunk),
                )
                continue

            try:
                pcm_chunk = self._normalise_audio_block(payload)
            except TextToSpeechError:
                raise
            except Exception as exc:  # pragma: no cover - backend dependent
                logger.warning(
                    "Skipping Piper audio payload %r: %s",
                    type(payload),
                    exc,
                )
                continue

            if pcm_chunk:
                yield pcm_chunk

    def _collect_chunks(self, chunks: Iterable[object]) -> bytes:
        """Normalise Piper chunk iterables into 16-bit PCM bytes."""
        return b"".join(self._iter_normalised_chunks(chunks))

    def _extract_audio_chunk(self, chunk: "AudioChunk") -> object | None:  # type: ignore[name-defined]
        """Extract the audio payload from a Piper ``AudioChunk`` instance."""
        self._maybe_update_sample_rate(getattr(chunk, "sample_rate", None))
        logger.debug("Inspecting Piper AudioChunk %s", self._describe_chunk(chunk))

        # Known modern Piper attributes that already expose byte or ndarray data.
        preferred_attrs = (
            "audio_int16_bytes",
            "audio_bytes",
            "audio",
            "buffer",
            "data",
            "pcm",
            "samples",
            "audio_int16_array",
            "audio_float_array",
            "audio_array",
        )

        for attr in preferred_attrs:
            payload = self._pluck_chunk_attribute(chunk, attr)
            if payload is not None:
                logger.debug("Resolved AudioChunk via attribute '%s'", attr)
                return payload

        # Some Piper releases expose helper methods such as ``to_bytes`` or
        # ``as_bytes``. Try those explicitly before falling back to the generic
        # resolver so that we can take advantage of any optimised conversions
        # provided by the library itself.
        for helper in ("to_bytes", "as_bytes"):
            payload = self._pluck_chunk_attribute(chunk, helper)
            if payload is not None:
                logger.debug("Resolved AudioChunk via helper '%s'", helper)
                return payload

        # Fall back to inspecting the public attributes dynamically. Some Piper
        # builds expose ``chunk.payload`` or other vendor-specific names that we
        # cannot predict ahead of time.
        for attr in dir(chunk):
            if attr.startswith("_"):
                continue
            payload = self._pluck_chunk_attribute(chunk, attr)
            if payload is not None:
                logger.debug("Resolved AudioChunk via dynamic attribute '%s'", attr)
                return payload

        # Last resort: rely on the generic payload resolver which walks common
        # attribute names and iterable interfaces.
        fallback = self._resolve_chunk_payload(chunk)
        if fallback is not None:
            logger.debug(
                "Resolved Piper AudioChunk via generic payload path (%s)",
                type(fallback).__name__,
            )
            return fallback

        logger.debug(
            "Unable to resolve Piper AudioChunk payload; summary=%s",
            self._describe_chunk(chunk),
        )
        return None

    def _pluck_chunk_attribute(self, chunk: object, attr: str) -> object | None:
        """Return a Piper chunk attribute value if it looks like audio data."""
        try:
            value = getattr(chunk, attr)
        except AttributeError:
            return None
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to access Piper chunk attribute %s: %s", attr, exc)
            return None

        if callable(value):
            try:
                value = value()
            except TypeError:
                return None
            except Exception as exc:  # pragma: no cover - backend dependent
                logger.debug("Callable Piper chunk attribute %s raised %s", attr, exc)
                return None

        if value in (None, ""):
            return None

        # Update sample rate hints if the attribute carries one.
        possible_rate = getattr(value, "sample_rate", None)
        if possible_rate is not None:
            self._maybe_update_sample_rate(possible_rate)

        if isinstance(value, (bytes, bytearray, memoryview)):
            return value

        if np is not None and isinstance(value, np.ndarray):
            return value

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return value

        if hasattr(value, "tobytes") or hasattr(value, "__iter__"):
            return value

        return None

    def _resolve_chunk_payload(self, chunk: object) -> object | None:
        """Extract raw audio-like payloads from Piper chunk objects."""
        visited: set[int] = set()
        current = chunk

        while True:
            if current is None:
                return None

            # Prevent infinite loops if Piper objects reference themselves.
            current_id = id(current)
            if current_id in visited:
                logger.debug("Detected cyclic Piper audio payload resolution for %r", current)
                return None
            visited.add(current_id)

            if isinstance(current, (bytes, bytearray, memoryview)):
                return current

            if np is not None and isinstance(current, np.ndarray):
                return current

            if isinstance(current, tuple):
                if len(current) == 0:
                    return b""
                if len(current) == 2:
                    possible_rate = current[1]
                    if possible_rate is not None:
                        self._maybe_update_sample_rate(possible_rate)
                    current = current[0]
                    continue

            if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
                return current

            sample_rate = getattr(current, "sample_rate", None)
            if sample_rate is not None:
                self._maybe_update_sample_rate(sample_rate)

            candidate = None
            for attr in (
                "audio_int16_bytes",
                "audio_bytes",
                "audio",
                "buffer",
                "data",
                "pcm",
                "samples",
                "audio_int16_array",
                "audio_float_array",
                "audio_array",
            ):
                try:
                    value = getattr(current, attr)
                except AttributeError:
                    continue

                if callable(value):  # pragma: no cover - defensive against callables
                    try:
                        value = value()
                    except TypeError:
                        continue

                if value is None:
                    continue

                candidate = value
                break

            if candidate is None:
                logger.debug(
                    "No audio payload discovered while resolving chunk %s; summary=%s",
                    type(current).__name__,
                    self._describe_chunk(current),
                )
                return None

            current = candidate

    def _floats_to_int16(self, array) -> "np.ndarray":  # type: ignore[name-defined]
        """Convert float PCM arrays to int16 for playback."""
        if np is None:
            raise TextToSpeechError("Piper returned floating-point audio but NumPy is unavailable")
        clipped = np.clip(array, -1.0, 1.0)
        return (clipped * 32767).astype(np.int16)

    def _extract_pcm(self, audio_bytes: bytes) -> bytes:
        """Return PCM data, decoding WAV headers when present."""
        if len(audio_bytes) >= 4 and audio_bytes[:4] == b"RIFF":
            try:
                with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                    channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                    if channels != 1:
                        logger.warning("Piper returned %s channels; only mono output is supported", channels)
                    if sample_width != 2:
                        logger.warning(
                            "Unexpected sample width %s; assuming 16-bit PCM for playback",
                            sample_width,
                        )
                    framerate = wf.getframerate()
                    if framerate and framerate != self._sample_rate:
                        logger.debug(
                            "Updating Piper sample rate from WAV header: %s -> %s",
                            self._sample_rate,
                            framerate,
                        )
                        self._sample_rate = framerate
                    return wf.readframes(wf.getnframes())
            except (wave.Error, EOFError) as exc:
                logger.warning("Failed to parse Piper WAV output (%s); treating audio as raw PCM", exc)
        return audio_bytes

    def _stream_pcm_chunks(self, chunks: Iterable[bytes]) -> None:
        """Play PCM audio chunks using PyAudio as they are produced."""
        iterator = iter(chunks)

        first_chunk: bytes | None = None
        for maybe_chunk in iterator:
            if maybe_chunk:
                first_chunk = maybe_chunk
                break

        if first_chunk is None:
            raise TextToSpeechError("Synthesiser returned no audio data")

        if self._sample_rate is None:
            raise TextToSpeechError("PCM playback requires a known sample rate")

        try:
            audio = pyaudio.PyAudio()
            try:
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self._sample_rate,
                    output=True,
                )
                try:
                    self._write_stream_chunk(stream, first_chunk)
                    for chunk in iterator:
                        if not chunk:
                            continue
                        self._write_stream_chunk(stream, chunk)
                finally:
                    stream.stop_stream()
                    stream.close()
            finally:
                audio.terminate()
        except Exception as exc:  # pragma: no cover - backend specific
            logger.exception("Failed to play PCM audio: %s", exc)
            raise TextToSpeechError("Failed to play PCM audio output") from exc

    def _write_stream_chunk(self, stream, data: bytes) -> None:
        """Write a block of PCM data to the active PyAudio stream."""
        if not data:
            return

        # Check if stop was requested before writing
        if self._stop_speech.is_set():
            logger.debug("Speech interrupted by stop signal")
            return

        chunk_size = 2048
        for start in range(0, len(data), chunk_size):
            # Check stop signal between chunks for responsiveness
            if self._stop_speech.is_set():
                logger.debug("Speech interrupted mid-chunk")
                return
            stream.write(data[start : start + chunk_size])

    def _normalise_audio_block(self, block: object) -> bytes:
        """Convert a Piper audio block into 16-bit PCM bytes."""
        if block is None:
            return b""

        if AudioChunk is not None and isinstance(block, AudioChunk):
            extractor = getattr(self, "_extract_audio_chunk", None)
            audio_payload = None
            if callable(extractor):
                audio_payload = extractor(block)
            if audio_payload is None:
                logger.warning(
                    "AudioChunk missing usable payload; summary=%s",
                    self._describe_chunk(block),
                )
                return b""
            return self._normalise_audio_block(audio_payload)

        if isinstance(block, (bytes, bytearray, memoryview)):
            return bytes(block)

        if np is not None and isinstance(block, np.ndarray):
            dtype = str(block.dtype)
            if dtype.startswith("float"):
                return self._floats_to_int16(block).tobytes()
            if dtype not in {"int16", "<i2"}:
                return block.astype(np.int16).tobytes()
            return block.tobytes()

        if hasattr(block, "tobytes"):
            try:
                return block.tobytes()  # type: ignore[return-value]
            except Exception:  # pragma: no cover - backend array quirk
                pass

        if isinstance(block, Sequence) and not isinstance(block, (str, bytes, bytearray)):
            if np is not None:
                array = np.asarray(block)
                if array.dtype.kind == "f":
                    return self._floats_to_int16(array).tobytes()
                if array.dtype != np.int16:
                    array = array.astype(np.int16)
                return array.tobytes()
            pcm_bytes = bytearray()
            for value in block:
                if isinstance(value, float):
                    value = max(-1.0, min(1.0, value))
                    value = int(value * 32767)
                else:
                    value = int(value)
                pcm_bytes.extend(int(value).to_bytes(2, "little", signed=True))
            return bytes(pcm_bytes)

        if hasattr(block, "__iter__"):
            if np is not None:
                array = np.fromiter(block, dtype=np.float32)
                return self._floats_to_int16(array).tobytes()
            pcm_bytes = bytearray()
            for value in block:
                if isinstance(value, float):
                    value = max(-1.0, min(1.0, value))
                    value = int(value * 32767)
                else:
                    value = int(value)
                pcm_bytes.extend(int(value).to_bytes(2, "little", signed=True))
            return bytes(pcm_bytes)

        return bytes(block)

    def _describe_chunk(self, chunk: object) -> str:
        """Return a lightweight description of a Piper chunk for logging."""
        try:
            details: list[str] = []
            for attr in dir(chunk):
                if attr.startswith("_"):
                    continue
                try:
                    value = getattr(chunk, attr)
                except Exception:
                    continue
                if callable(value):
                    details.append(f"{attr}()")
                    continue
                if isinstance(value, (bytes, bytearray, memoryview)):
                    details.append(f"{attr}=bytes[{len(value)}]")
                    continue
                if np is not None and isinstance(value, np.ndarray):
                    details.append(f"{attr}=ndarray(shape={value.shape},dtype={value.dtype})")
                    continue
                if isinstance(value, (int, float)):
                    details.append(f"{attr}={value}")
                    continue
                if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                    details.append(f"{attr}=sequence(len={len(value)})")
                    continue
                summary = type(value).__name__
                details.append(f"{attr}={summary}")
                if len(details) >= 8:
                    break
        except Exception as exc:
            return f"<uninspectable: {exc}>"
        if not details:
            return "<no public attributes>"
        return ", ".join(details)

    def _resolve_sample_rate(self, voice_path: Path) -> int:
        """Determine the Piper voice sample rate for PCM fallback."""
        # Piper voices often ship with a neighbouring JSON metadata file that
        # advertises the audio sample rate. Prefer that when present so that we
        # can stream headerless PCM confidently.
        metadata_path = voice_path.with_suffix(".json")
        if metadata_path.exists():
            try:
                with metadata_path.open("r", encoding="utf-8") as handle:
                    metadata = json.load(handle)
                sample_rate = metadata.get("audio", {}).get("sample_rate")
                if sample_rate:
                    logger.debug("Loaded Piper sample rate %sHz from %s", sample_rate, metadata_path)
                    return int(sample_rate)
            except Exception as exc:  # pragma: no cover - metadata optional
                logger.warning("Unable to read Piper metadata from %s: %s", metadata_path, exc)

        # Fallback to any attribute provided by the Piper voice instance.
        sample_rate_attr = getattr(self._voice, "sample_rate", None)
        if sample_rate_attr:
            try:
                sample_rate = int(sample_rate_attr)
            except (TypeError, ValueError):
                logger.debug("Unexpected Piper sample_rate attribute: %r", sample_rate_attr)
            else:
                logger.debug("Using Piper voice sample_rate attribute: %s", sample_rate)
                return sample_rate

        logger.debug("Piper sample rate could not be determined from metadata; defaulting to 22050Hz")
        return 22050

    def _maybe_update_sample_rate(self, value: object) -> None:
        """Update the playback sample rate when Piper supplies one."""
        if value in (None, ""):
            return
        try:
            sample_rate = int(value)
        except (TypeError, ValueError):
            logger.debug("Unexpected Piper sample rate payload: %r", value)
            return
        if sample_rate > 0:
            if sample_rate != self._sample_rate:
                logger.debug(
                    "Updating Piper sample rate: %s -> %s",
                    self._sample_rate,
                    sample_rate,
                )
            self._sample_rate = sample_rate


__all__ = ["TextToSpeech", "TextToSpeechError"]
