"""Entry point for running Freya with MCP-backed orchestration.

This script wires together wake-word detection, audio capture, MCP tool
servers, and the MCP-aware orchestrator loop so Freya can listen and respond
hands-free.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Optional

import soundfile as sf

from freya.coordination.orchestrator_mcp import MCPOrchestrator
from freya.core.config import Settings, load_settings
from freya.core.context import ConversationContext
from freya.core.logger import get_logger
from freya.core.ollama_client import OllamaClient
from freya_mcp.client import FreyaMCPClient, MCPServerConfig
from freya.voice.stt import SpeechToText, SpeechToTextError
from freya.voice.wake import WakeWordDetector, WakeWordDetectorError
from freya.voice.wake_word_matcher import WakeWordMatcher

logger = get_logger("freya.mcp.start")


def _build_mcp_client() -> FreyaMCPClient:
    """Create an MCP client with the system and audio servers configured."""

    python = sys.executable
    client = FreyaMCPClient(
        [
            MCPServerConfig(
                name="system",
                command=[python, "-m", "freya_mcp.servers.freya_system_server.server"],
            ),
            MCPServerConfig(
                name="audio",
                command=[python, "-m", "freya_mcp.servers.freya_audio_server.server"],
            ),
        ]
    )
    return client


def _build_context(system_prompt: str, settings: Settings) -> ConversationContext:
    short_term = settings.memory.short_term
    return ConversationContext(
        system_prompt=system_prompt,
        max_history=short_term.max_history,
        enable_summarization=short_term.enable_summarization,
        summary_trigger_ratio=short_term.summary_trigger_ratio,
        max_summaries=short_term.max_summaries,
    )


def _record_command_audio(stt: SpeechToText) -> Path:
    """Capture a spoken command and persist it to a temporary WAV file."""

    stt.play_prompt_tone()
    recording = stt._record_until_silence()  # type: ignore[attr-defined]
    if recording.samples.size == 0:
        raise SpeechToTextError("No audio captured")

    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = Path(handle.name)
    sf.write(handle, recording.samples, recording.samplerate)
    handle.close()
    return temp_path


def _handle_wake_loop(
    orchestrator: MCPOrchestrator,
    wake_detector: WakeWordDetector,
    wake_matcher: WakeWordMatcher,
    stt: SpeechToText,
) -> None:
    """Listen for the wake word and forward recorded audio to the orchestrator."""

    logger.info("Listening for '%s'...", wake_matcher.wake_word_display)
    while True:
        try:
            transcript = wake_detector.listen_once()
        except WakeWordDetectorError as exc:
            logger.error("Wake detector failure: %s", exc)
            break

        detected, _ = wake_matcher.find_wake_word(transcript)
        if not detected:
            continue

        logger.info("Wake word detected; recording command audio")
        try:
            audio_path = _record_command_audio(stt)
        except SpeechToTextError as exc:
            logger.error("Failed to record command audio: %s", exc)
            continue

        try:
            reply = orchestrator.handle_audio_input(str(audio_path))
            logger.info("Freya: %s", reply)
        finally:
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                logger.debug("Could not delete temporary audio file: %s", audio_path)


def main() -> None:
    settings: Settings = load_settings()
    mcp_client = _build_mcp_client()
    llm_client = OllamaClient(settings.ollama)
    context = _build_context(settings.app.system_prompt, settings)
    orchestrator = MCPOrchestrator(llm_client, mcp_client, context, auto_speak=True)

    wake_detector: Optional[WakeWordDetector] = None
    try:
        wake_detector = WakeWordDetector(settings.wake_detector)
    except WakeWordDetectorError as exc:
        logger.error("Wake detector unavailable: %s", exc)
        return

    wake_matcher = WakeWordMatcher(
        wake_word=settings.app.wake_word,
        sensitivity=settings.app.wake_word_sensitivity,
    )
    stt = SpeechToText(settings.stt)

    try:
        orchestrator.warm_up_tools()
        _handle_wake_loop(orchestrator, wake_detector, wake_matcher, stt)
    finally:
        mcp_client.stop_servers()
        if wake_detector is not None:
            wake_detector.close()


if __name__ == "__main__":
    main()
