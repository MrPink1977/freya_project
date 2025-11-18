"""Runtime diagnostics for Freya's voice assistant stack."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

try:  # pragma: no cover - optional dependency is exercised at runtime
    from colorama import Fore, Style
except ImportError:  # pragma: no cover - colorama is optional but recommended
    Fore = Style = None  # type: ignore[assignment]

from .config import FaceRecognitionConfig, LongTermMemoryConfig, WakeDetectorConfig
from .logger import get_logger

logger = get_logger("system_check")


class SystemCheck:
    """Run diagnostic checks on Freya's components."""

    def _check_ollama(self, host: str, model: str | None) -> Tuple[bool, str]:
        """Check if Ollama is reachable and confirm the configured model exists."""
        try:
            import requests

            response = requests.get(f"{host.rstrip('/')}/api/tags", timeout=5)
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect - is Ollama running?"
        except Exception as exc:  # pragma: no cover - network/runtime specific
            logger.exception("Unexpected error while checking Ollama: %s", exc)
            return False, str(exc)

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        models = response.json().get("models", [])
        if not models:
            return False, "No models available"

        if model:
            desired = model.strip()
            if desired:
                available = {entry.get("name", "") for entry in models}
                if desired not in available:
                    sample = ", ".join(sorted(filter(None, available))[:5])
                    if sample:
                        sample = f" Available: {sample}"
                    return False, f"Model '{desired}' not installed.{sample}"
                return True, f"Model '{desired}' ready"

        return True, f"Found {len(models)} model(s)"

    def _check_microphone(self) -> Tuple[bool, str]:
        """Check whether the default microphone can be accessed."""
        try:
            import sounddevice as sd
        except ImportError as exc:  # pragma: no cover - optional dependency
            return False, f"sounddevice missing: {exc}"

        try:
            with sd.InputStream(channels=1, samplerate=16000):
                pass
        except Exception as exc:  # pragma: no cover - depends on hardware state
            logger.exception("Microphone check failed: %s", exc)
            return False, f"Cannot access mic: {exc}"
        return True, "Microphone accessible"

    def _check_whisper(self, device: str) -> Tuple[bool, str]:
        """Check if faster-whisper can run on the requested device."""
        try:
            from faster_whisper import WhisperModel  # noqa: F401
        except ImportError as exc:  # pragma: no cover - optional dependency
            return False, f"faster-whisper not available: {exc}"

        requested = (device or "auto").strip().lower()

        def _cuda_available() -> bool:
            try:
                import ctranslate2  # type: ignore

                if ctranslate2.get_device_count("cuda") > 0:
                    return True
            except Exception:  # pragma: no cover - probing errors
                logger.debug("ctranslate2 CUDA probe failed", exc_info=True)

            try:
                import torch

                return bool(torch.cuda.is_available())
            except Exception:  # pragma: no cover - torch optional
                return False

        if requested in {"", "auto"}:
            if _cuda_available():
                try:
                    import torch

                    return True, f"GPU available: {torch.cuda.get_device_name(0)}"
                except Exception:
                    return True, "CUDA device available"
            return True, "Using CPU"

        if requested.startswith("cuda"):
            if not _cuda_available():
                return False, "CUDA requested but unavailable - falling back to CPU"
            try:
                import torch

                return True, f"CUDA available: {torch.cuda.get_device_name(0)}"
            except Exception:
                return True, "CUDA device available"

        return True, "Using CPU"

    def _check_tts(self, voice_path: str) -> Tuple[bool, str]:
        """Check if the Piper TTS engine is ready."""
        try:
            from piper import PiperVoice
        except ImportError as exc:  # pragma: no cover - optional dependency
            return False, f"piper-tts missing: {exc}"

        try:
            import pyaudio  # noqa: F401  # pragma: no cover - import check only
        except ImportError as exc:  # pragma: no cover - optional dependency
            return False, f"pyaudio missing: {exc}"

        voice_file = Path(voice_path).expanduser()
        if not voice_file.exists():
            return False, f"Voice file not found: {voice_file}"

        try:
            _voice = PiperVoice.load(str(voice_file))
        except Exception as exc:  # pragma: no cover - depends on model integrity
            logger.exception("Piper voice validation failed: %s", exc)
            return False, f"Failed to load voice: {exc}"

        # Explicitly drop reference to free resources prior to runtime initialisation.
        del _voice

        return True, "Piper voice ready"

    def _colour(self, text: str, colour: str) -> str:
        if Fore is None or Style is None:
            return text
        return f"{colour}{text}{Style.RESET_ALL}"

    def _print_check(self, name: str, passed: bool, message: str) -> bool:
        """Print a single check result with colourised status."""
        if passed:
            icon = self._colour("✓", Fore.GREEN if Fore else "")
            status = self._colour("OK", Fore.GREEN if Fore else "")
        else:
            icon = self._colour("✗", Fore.RED if Fore else "")
            status = self._colour("FAIL", Fore.RED if Fore else "")

        print(f"  {icon} {name:<20} [{status}]  {message}")
        return passed

    def _check_memory(self, config: LongTermMemoryConfig) -> Tuple[bool, str]:
        """Validate long-term memory configuration and storage accessibility."""

        if not config.enabled:
            return True, "Long-term memory disabled"

        store_type = (config.store_type or "sqlite").strip().lower()
        if store_type != "sqlite":
            return False, f"Unsupported store type: {config.store_type}"

        try:
            from .memory import PersistentMemoryStore

            store = PersistentMemoryStore(
                config.db_path,
                embedding_model=config.embedding_model,
            )
            try:
                # Opening the store ensures the backing database is writable.
                pass
            finally:
                store.close()
        except ImportError as exc:  # pragma: no cover - dependency missing
            return False, f"Memory store dependencies missing: {exc}"
        except Exception as exc:  # pragma: no cover - runtime specific
            logger.exception("Memory check failed: %s", exc)
            return False, f"Failed to initialise memory store: {exc}"

        return True, f"SQLite store ready ({config.db_path})"

    def _check_wake_detector(self, config: WakeDetectorConfig) -> Tuple[bool, str]:
        """Validate wake detector dependencies and configuration."""

        if config.sample_rate <= 0:
            return False, "Invalid sample rate"
        if config.chunk_seconds <= 0:
            return False, "Invalid chunk duration"

        try:
            from .wake import WakeWordDetector, WakeWordDetectorError
        except ImportError as exc:  # pragma: no cover - module missing
            return False, f"Wake detector unavailable: {exc}"

        try:
            detector = WakeWordDetector(config)
        except WakeWordDetectorError as exc:
            return False, str(exc)
        except Exception as exc:  # pragma: no cover - backend specific
            logger.exception("Wake detector check failed: %s", exc)
            return False, f"Failed to initialise wake detector: {exc}"
        else:
            detector.close()
        return True, f"Model '{config.model}' ready"

    def _check_facial_recognition(self, config: FaceRecognitionConfig) -> Tuple[bool, str]:
        """Validate facial recognition configuration and dependencies."""

        if not config.enabled:
            return True, "Facial recognition disabled"

        directory = Path(config.known_faces_dir).expanduser()
        if not directory.exists():
            return False, f"Known faces directory missing: {directory}"

        try:
            from .facial_recognition import FaceRecognitionError, FacialRecognition
        except ImportError as exc:  # pragma: no cover - optional dependency missing
            return False, f"Facial recognition module unavailable: {exc}"

        try:
            recogniser = FacialRecognition(config, eager_load=True)
        except FaceRecognitionError as exc:
            return False, str(exc)
        except Exception as exc:  # pragma: no cover - backend specific
            logger.exception("Facial recognition check failed: %s", exc)
            return False, f"Failed to initialise facial recognition: {exc}"
        else:
            known = recogniser.known_face_names
            count = len(known)
            del recogniser
            if count:
                return True, f"Loaded {count} known face(s)"
            return True, "No known faces configured"

    def run_all_checks(
        self,
        ollama_host: str,
        ollama_model: str,
        stt_device: str,
        tts_voice_path: str,
        memory_config: LongTermMemoryConfig,
        wake_config: WakeDetectorConfig,
        face_config: FaceRecognitionConfig,
    ) -> bool:
        """Run diagnostics and return True if all checks pass."""
        title_colour = Fore.CYAN if Fore else ""
        reset = Style.RESET_ALL if Style else ""
        print(f"\n{title_colour}{'=' * 60}")
        print("  FREYA SYSTEM CHECK")
        print(f"{'=' * 60}{reset}\n")

        all_passed = True
        checks = [
            ("Ollama", *self._check_ollama(ollama_host, ollama_model)),
            ("Microphone", *self._check_microphone()),
            ("STT (faster-whisper)", *self._check_whisper(stt_device)),
            ("Wake Detector", *self._check_wake_detector(wake_config)),
            ("Text-to-Speech", *self._check_tts(tts_voice_path)),
            ("Memory", *self._check_memory(memory_config)),
            ("Facial Recognition", *self._check_facial_recognition(face_config)),
        ]

        for name, passed, message in checks:
            all_passed &= self._print_check(name, passed, message)

        print()
        if all_passed:
            print(self._colour("✓ All systems operational!\n", Fore.GREEN if Fore else ""))
            return True

        print(self._colour("⚠ Some systems failed - check errors above\n", Fore.RED if Fore else ""))
        response = input("Continue anyway? (y/n): ")
        return response.strip().lower() == "y"


def run_system_check(
    ollama_host: str,
    ollama_model: str,
    stt_device: str,
    tts_voice_path: str,
    memory_config: LongTermMemoryConfig,
    wake_config: WakeDetectorConfig,
    face_config: FaceRecognitionConfig,
) -> bool:
    """Convenience helper to run the full diagnostic suite."""
    checker = SystemCheck()
    return checker.run_all_checks(
        ollama_host,
        ollama_model,
        stt_device,
        tts_voice_path,
        memory_config,
        wake_config,
        face_config,
    )
