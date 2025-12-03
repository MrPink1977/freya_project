"""Minimal MCP audio server exposing speech-to-text tools."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from freya.core.config import load_settings
from freya.core.logger import get_logger
from freya.voice.stt import SpeechToText, SpeechToTextError
from freya.voice.tts import TextToSpeechError, create_tts

logger = get_logger("mcp.audio")


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    args_schema: Dict[str, Any] | None = None


tool_metadata: List[MCPTool] = [
    MCPTool(
        name="freya.audio.transcribe",
        description="Transcribe an audio file using Freya's speech-to-text stack.",
        args_schema={
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    ),
    MCPTool(
        name="freya.audio.speak_el",
        description="Speak text aloud using the ElevenLabs TTS configuration.",
        args_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    ),
    MCPTool(
        name="freya.audio.list_tools",
        description="Return metadata for all tools exposed by the audio MCP server.",
        args_schema={"type": "object", "properties": {}},
    ),
]


def _list_tools_handler(_: Dict[str, Any]) -> Dict[str, Any]:
    """Return metadata for all tools exposed by this MCP server."""

    return {
        "type": "tool_result",
        "tool": "freya.audio.list_tools",
        "success": True,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema,
            }
            for tool in tool_metadata
        ],
    }


_STT: SpeechToText | None = None
_TTS: Any | None = None


def _get_stt() -> SpeechToText:
    """Lazily construct a SpeechToText instance using configured settings."""

    global _STT
    if _STT is None:
        settings = load_settings()
        _STT = SpeechToText(settings.stt)
    return _STT


def _get_elevenlabs_tts():
    """Lazily construct an ElevenLabs-backed TTS instance."""

    global _TTS
    if _TTS is None:
        settings = load_settings()
        engine = settings.tts.engine.lower()
        if engine != "elevenlabs":
            raise TextToSpeechError(
                f"TTS engine is '{engine}', but freya.audio.speak_el requires 'elevenlabs'"
            )

        _TTS = create_tts(settings.tts)
    return _TTS


def _transcribe_audio_file(audio_path: Path) -> str:
    """Transcribe the provided audio file using faster-whisper."""

    stt = _get_stt()
    segments, info = stt._model.transcribe(  # type: ignore[attr-defined]
        str(audio_path),
        beam_size=1,
        best_of=1,
        temperature=0.0,
        vad_filter=True,
    )
    pieces = [segment.text.strip() for segment in segments if getattr(segment, "text", "")]
    text = " ".join(filter(None, pieces)).strip()
    if info.language:
        logger.debug(
            "Detected language: %s (prob=%.3f)", info.language, info.language_probability
        )
    return text


def transcribe_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Transcribe an audio file and return the text."""

    file_path = args.get("file_path")
    if not file_path:
        return {
            "type": "tool_result",
            "tool": "freya.audio.transcribe",
            "success": False,
            "error": "Argument 'file_path' is required",
        }

    audio_path = Path(file_path)
    if not audio_path.exists():
        return {
            "type": "tool_result",
            "tool": "freya.audio.transcribe",
            "success": False,
            "error": f"Audio file not found: {audio_path}",
        }

    try:
        transcript = _transcribe_audio_file(audio_path)
    except SpeechToTextError as exc:
        logger.exception("Speech-to-text failed: %s", exc)
        return {
            "type": "tool_result",
            "tool": "freya.audio.transcribe",
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - defensive catch for unexpected failures
        logger.exception("Unexpected error during transcription: %s", exc)
        return {
            "type": "tool_result",
            "tool": "freya.audio.transcribe",
            "success": False,
            "error": str(exc),
        }

    return {
        "type": "tool_result",
        "tool": "freya.audio.transcribe",
        "success": True,
        "text": transcript,
    }


def speak_elevenlabs_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Speak text using the configured ElevenLabs TTS engine."""

    text = args.get("text")
    if not text:
        return {
            "type": "tool_result",
            "tool": "freya.audio.speak_el",
            "success": False,
            "error": "Argument 'text' is required",
        }

    try:
        tts = _get_elevenlabs_tts()
    except TextToSpeechError as exc:
        logger.exception("TTS initialization failed: %s", exc)
        return {
            "type": "tool_result",
            "tool": "freya.audio.speak_el",
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - defensive catch for unexpected failures
        logger.exception("Unexpected error during TTS initialization: %s", exc)
        return {
            "type": "tool_result",
            "tool": "freya.audio.speak_el",
            "success": False,
            "error": str(exc),
        }

    try:
        tts.speak(str(text))
    except TextToSpeechError as exc:
        logger.exception("TTS synthesis failed: %s", exc)
        return {
            "type": "tool_result",
            "tool": "freya.audio.speak_el",
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - defensive catch for unexpected failures
        logger.exception("Unexpected error during TTS playback: %s", exc)
        return {
            "type": "tool_result",
            "tool": "freya.audio.speak_el",
            "success": False,
            "error": str(exc),
        }

    return {
        "type": "tool_result",
        "tool": "freya.audio.speak_el",
        "success": True,
    }


tool_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "freya.audio.list_tools": _list_tools_handler,
    "freya.audio.transcribe": transcribe_handler,
    "freya.audio.speak_el": speak_elevenlabs_handler,
}


def _iter_requests(stream: Iterable[str]) -> Iterable[Dict[str, Any]]:
    """Yield decoded JSON requests from an input stream."""

    for line in stream:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            yield {"type": "error", "error": "Invalid JSON"}


def _serialize_response(response: Dict[str, Any]) -> str:
    """Serialize responses as single-line JSON for stdout."""

    return json.dumps(response, ensure_ascii=False)


def _handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a single MCP request."""

    if request.get("type") == "list_tools":
        return {
            "type": "tool_list",
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": tool.args_schema,
                }
                for tool in tool_metadata
            ],
        }

    if request.get("type") == "call_tool":
        tool_name = request.get("tool")
        args = request.get("args") or {}

        handler = tool_handlers.get(tool_name)
        if handler:
            return handler(args)

        return {
            "type": "tool_result",
            "tool": tool_name,
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }

    return {"type": "error", "error": "Unsupported request"}


def main() -> None:
    """Run the request loop."""

    for request in _iter_requests(sys.stdin):
        response = _handle_request(request)
        sys.stdout.write(_serialize_response(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
