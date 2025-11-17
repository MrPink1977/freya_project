"""
ENTRY POINT FOR THE FREYA VOICE-ENABLED ASSISTANT.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

from freya.config import AppConfig, load_settings
from freya.context import ConversationContext
from freya.logger import configure_logging, get_logger
from freya.memory import PersistentMemoryStore
from freya.ollama_client import OllamaClient
from freya.orchestrator import Orchestrator
from freya.stt import SpeechToText, SpeechToTextError
from freya.system_check import run_system_check
from freya.tts import TextToSpeech, TextToSpeechError, create_tts
from freya.wake import WakeWordDetector, WakeWordDetectorError


class StartupMode(str, Enum):
    """Available startup display modes for Freya."""

    NORMAL = "normal"
    DIAGNOSTIC = "diagnostic"


def _parse_mode(value: str) -> StartupMode:
    if value.lower() == StartupMode.DIAGNOSTIC.value:
        return StartupMode.DIAGNOSTIC
    return StartupMode.NORMAL


def _select_startup_mode(app_config: AppConfig) -> StartupMode:
    """Select startup mode based on configuration.

    This function respects app_config.startup_mode and app_config.prompt_for_mode.
    If prompt_for_mode is enabled the user is prompted (unless non-interactive),
    otherwise the configured default is returned.
    """
    default_mode = _parse_mode(app_config.startup_mode)
    if not app_config.prompt_for_mode:
        return default_mode

    # If stdin is not a TTY (non-interactive), fall back to default without prompting
    try:
        if not os.isatty(0):  # pragma: no cover - environment specific
            return default_mode
    except Exception:
        # If the platform doesn't support isatty, continue to attempt prompt
        pass

    prompt = (
        "Select startup mode - [N]ormal or [D]iagnostic "
        f"(default: {default_mode.value.title()}): "
    )
    try:
        choice = input(prompt).strip().lower()
    except EOFError:
        choice = ""

    if not choice:
        return default_mode
    if choice in {"n", "normal"}:
        return StartupMode.NORMAL
    if choice in {"d", "diagnostic"}:
        return StartupMode.DIAGNOSTIC
    return default_mode


_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _build_output(mode: StartupMode) -> Callable[[str], None]:
    if mode is StartupMode.NORMAL:
        def _normal_output(message: str) -> None:
            normalized = _ANSI_PATTERN.sub("", message)
            if normalized.startswith("You said:") or normalized.startswith("Freya:"):
                print(message)

        return _normal_output

    return print


def backup_memory(db_path: str, logger: logging.Logger) -> None:
    """Create a timestamped backup of Freya's memory database.

    Args:
        db_path: Path to the memory database file
        logger: Logger instance for recording backup status
    """
    if not db_path:
        logger.debug("No database path provided; skipping backup")
        return

    db_file = Path(db_path).expanduser()
    if not db_file.exists():
        logger.debug("Memory database does not exist yet; skipping backup")
        return

    # Check if file is accessible (prevents corruption from locked files)
    try:
        with open(db_file, 'rb') as f:
            pass
    except (IOError, PermissionError) as exc:
        logger.warning("Cannot access database file for backup: %s", exc)
        return

    # Create backup directory next to the database
    backup_dir = db_file.parent / "backups"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Failed to create backup directory: %s", exc)
        return

    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{db_file.stem}_{timestamp}{db_file.suffix}"

    try:
        shutil.copy2(str(db_file), str(backup_file))
        logger.info("Memory backed up to: %s", backup_file)
        print(f"Memory backed up: {backup_file}")
    except (OSError, shutil.Error) as exc:
        logger.warning("Failed to backup memory database: %s", exc)


def main() -> None:
    # Parse CLI args and environment overrides first so we can run non-interactively
    parser = argparse.ArgumentParser(prog="freya", description="Freya voice assistant")
    parser.add_argument(
        "--startup-mode",
        choices=[StartupMode.NORMAL.value, StartupMode.DIAGNOSTIC.value],
        help="Select startup mode (overrides config)",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Do not prompt for startup mode (non-interactive)",
    )

    # Use parse_known_args to be tolerant of other args used by downstream callers
    args, _ = parser.parse_known_args()

    # Load settings and apply overrides from env/CLI
    settings = load_settings()

    # Environment variable override: FREYA_STARTUP_MODE
    env_mode = os.getenv("FREYA_STARTUP_MODE")
    if env_mode:
        settings.app.startup_mode = env_mode

    # Environment variable to control prompting: FREYA_PROMPT_FOR_MODE (1/0, true/false)
    env_prompt = os.getenv("FREYA_PROMPT_FOR_MODE")
    if env_prompt is not None:
        settings.app.prompt_for_mode = env_prompt.lower() in ("1", "true", "yes")

    # CLI overrides take precedence
    if args.startup_mode:
        settings.app.startup_mode = args.startup_mode
    if args.no_prompt:
        settings.app.prompt_for_mode = False

    mode = _select_startup_mode(settings.app)

    console_level = logging.INFO if mode is StartupMode.DIAGNOSTIC else logging.ERROR
    configure_logging(
        file_level=logging.INFO,
        console_level=console_level,
        force=True,
    )

    logger = get_logger("main")
    logger.info("Loaded settings from configuration")
    logger.info("Startup mode selected: %s", mode.value)

    if not run_system_check(
        settings.ollama.host,
        settings.ollama.model,
        settings.stt.device,
        settings.tts.voice_path,
        settings.memory.long_term,
        settings.wake_detector,
        settings.vision.facial_recognition,
    ):
        logger.error("System diagnostics failed; aborting startup")
        raise SystemExit(1)

    client = OllamaClient(settings.ollama)
    context = ConversationContext(
        system_prompt=settings.app.system_prompt,
        max_history=settings.memory.short_term.max_history,
        enable_summarization=settings.memory.short_term.enable_summarization,
        summary_trigger_ratio=settings.memory.short_term.summary_trigger_ratio,
        max_summaries=settings.memory.short_term.max_summaries,
    )
    memory_store: PersistentMemoryStore | None = None
    if settings.memory.long_term.enabled:
        try:
            memory_store = PersistentMemoryStore(settings.memory.long_term.db_path)
        except Exception as exc:  # pragma: no cover - runtime specific
            logger.error("Failed to initialise long-term memory store: %s", exc)
    try:
        stt = SpeechToText(settings.stt)
    except SpeechToTextError as exc:
        logger.error("Failed to initialize speech-to-text: %s", exc)
        raise SystemExit(
            "Speech input is unavailable. Install the required voice dependencies (see README)."
        ) from exc

    try:
        tts = create_tts(settings.tts)
    except TextToSpeechError as exc:
        logger.error("Failed to initialize text-to-speech: %s", exc)
        raise SystemExit(
            "Speech output is unavailable. Install the required voice dependencies (see README)."
        ) from exc

    wake_detector: WakeWordDetector | None = None
    try:
        wake_detector = WakeWordDetector(settings.wake_detector)
    except WakeWordDetectorError as exc:
        logger.warning("Wake detector unavailable: %s", exc)
    except Exception as exc:  # pragma: no cover - runtime specific
        logger.exception("Failed to initialise wake detector: %s", exc)
        wake_detector = None

    facial_recognition = None
    if settings.vision.facial_recognition.enabled:
        try:
            from freya.facial_recognition import FacialRecognition

            facial_recognition = FacialRecognition(settings.vision.facial_recognition)
            logger.info(
                "Facial recognition initialised with %d known face(s)",
                len(facial_recognition.known_face_names),
            )
        except Exception as exc:  # pragma: no cover - backend specific
            # Consolidate and log unexpected issues; specific errors are handled inside module
            logger.exception("Unexpected error initialising facial recognition: %s", exc)
            facial_recognition = None

    output_fn = _build_output(mode)

    orchestrator = Orchestrator(
        client=client,
        context=context,
        stt=stt,
        tts=tts,
        output_fn=output_fn,
        wake_word=settings.app.wake_word,
        wake_sensitivity=settings.app.wake_word_sensitivity,
        session_window=settings.app.wake_session_seconds,
        memory_store=memory_store,
        memory_config=settings.memory.long_term,
        interaction_mode=settings.app.interaction_mode,
        mode_toggle_hotkey=settings.app.mode_toggle_hotkey,
        wake_detector=wake_detector,
    )

    try:
        orchestrator.run()
    finally:
        # Always backup memory on exit, even if interrupted
        if settings.memory.long_term.enabled:
            backup_memory(settings.memory.long_term.db_path, logger)


if __name__ == "__main__":
    main()
