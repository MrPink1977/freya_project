"""Text-to-speech using ElevenLabs MCP server for high-quality voice synthesis."""

from __future__ import annotations

import asyncio
import io
import os
import subprocess
import json
import threading
from pathlib import Path
from typing import Optional

try:
    import pyaudio
except ImportError as exc:
    pyaudio = None  # type: ignore[assignment]
    _PYAUDIO_ERROR = exc
else:
    _PYAUDIO_ERROR = None

try:
    from pydub import AudioSegment
except ImportError as exc:
    AudioSegment = None  # type: ignore[assignment,misc]
    _PYDUB_ERROR = exc
else:
    _PYDUB_ERROR = None

from freya.core.logger import get_logger

logger = get_logger("tts.elevenlabs.mcp")


class TextToSpeechError(RuntimeError):
    """Raised when synthesising or playing speech fails."""


class ElevenLabsMCPTTS:
    """Convert text responses into spoken audio output using ElevenLabs MCP server."""

    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel - default voice
        model_id: str = "eleven_turbo_v2_5",  # Fastest, lowest latency
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        speed: float = 1.0,
    ) -> None:
        """Initialize ElevenLabs MCP TTS.

        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use (default: Rachel)
            model_id: Model to use (turbo_v2_5 for speed, multilingual_v2 for quality)
            stability: Voice stability (0-1, higher = more stable/consistent)
            similarity_boost: Voice similarity (0-1, higher = more similar to original)
            style: Style exaggeration (0-1, higher = more expressive)
            use_speaker_boost: Enable speaker boost for clarity
            speed: Speech speed (0.7-1.2, default 1.0)
        """
        if _PYDUB_ERROR is not None:
            raise TextToSpeechError(
                "Audio dependency missing: pydub (pip install pydub)"
            ) from _PYDUB_ERROR
        if _PYAUDIO_ERROR is not None:
            raise TextToSpeechError(
                "Audio playback dependency missing: pyaudio (pip install pyaudio)"
            ) from _PYAUDIO_ERROR

        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._stability = stability
        self._similarity_boost = similarity_boost
        self._style = style
        self._use_speaker_boost = use_speaker_boost
        self._speed = speed
        self._stop_speech = threading.Event()

        # Find the MCP server script
        self._server_script = self._find_mcp_server()

        logger.info(
            "Initialized ElevenLabs MCP TTS with voice_id=%s, model=%s",
            voice_id,
            model_id,
        )

    def _find_mcp_server(self) -> str:
        """Find the ElevenLabs MCP server script."""
        # Try to find the server in the installed package
        try:
            import elevenlabs_mcp
            package_dir = Path(elevenlabs_mcp.__file__).parent
            server_path = package_dir / "server.py"
            if server_path.exists():
                return str(server_path)
        except ImportError:
            pass

        raise TextToSpeechError(
            "ElevenLabs MCP server not found. Install with: pip install elevenlabs-mcp"
        )

    async def _call_mcp_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool via subprocess and return the result.
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Dictionary containing the tool result
        """
        # Create MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Set environment variables
        env = os.environ.copy()
        env["ELEVENLABS_API_KEY"] = self._api_key
        env["ELEVENLABS_MCP_OUTPUT_MODE"] = "resources"  # Get audio data directly

        # Call MCP server
        try:
            process = await asyncio.create_subprocess_exec(
                "python",
                self._server_script,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Send request and get response
            stdout, stderr = await process.communicate(
                input=json.dumps(request).encode()
            )

            if stderr:
                logger.debug("MCP server stderr: %s", stderr.decode())

            # Parse response
            response = json.loads(stdout.decode())
            
            if "error" in response:
                raise TextToSpeechError(
                    f"MCP tool error: {response['error'].get('message', 'Unknown error')}"
                )

            return response.get("result", {})

        except Exception as exc:
            logger.exception("Failed to call MCP tool: %s", exc)
            raise TextToSpeechError(f"Failed to call MCP tool '{tool_name}'") from exc

    def speak(self, text: str) -> None:
        """Synthesize and play the provided text using ElevenLabs MCP.

        Args:
            text: Text to convert to speech
        """
        if not text or not text.strip():
            logger.debug("No text provided for speech output")
            return

        # Clear stop flag at start of new speech
        self._stop_speech.clear()

        trimmed = text.strip()
        logger.info("Speaking response: %s", trimmed[:1000])

        try:
            # Call MCP text_to_speech tool asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._call_mcp_tool(
                        "text_to_speech",
                        {
                            "text": trimmed,
                            "voice_id": self._voice_id,
                            "model_id": self._model_id,
                            "stability": self._stability,
                            "similarity_boost": self._similarity_boost,
                            "style": self._style,
                            "use_speaker_boost": self._use_speaker_boost,
                            "speed": self._speed,
                        }
                    )
                )
            finally:
                loop.close()

            # Extract audio data from MCP response
            # MCP returns embedded resource with base64 audio data
            if "contents" in result and len(result["contents"]) > 0:
                content = result["contents"][0]
                if "blob" in content:
                    import base64
                    audio_data = base64.b64decode(content["blob"])
                    self._play_audio(audio_data)
                else:
                    raise TextToSpeechError("No audio data in MCP response")
            else:
                raise TextToSpeechError("Invalid MCP response format")

        except Exception as exc:
            logger.exception("Failed to synthesize or play speech: %s", exc)
            raise TextToSpeechError("Failed to synthesize speech with ElevenLabs MCP") from exc

    def stop_speaking(self) -> None:
        """Signal the TTS to stop current playback."""
        self._stop_speech.set()
        logger.debug("Stop speech signal set")

    def preload_phrase(self, text: str) -> None:
        """Preload a phrase (no-op for MCP streaming).

        MCP uses on-demand API calls, so preloading isn't beneficial.
        This method is kept for interface compatibility.
        """
        logger.debug("Preload requested for '%s' (no-op for MCP API)", text[:50])

    def _play_audio(self, audio_data: bytes) -> None:
        """Play audio data from ElevenLabs MCP.

        Args:
            audio_data: Audio bytes from MCP (MP3 format)
        """
        try:
            # ElevenLabs returns MP3 audio, decode it to raw PCM
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))

            # Convert to raw audio data
            raw_data = audio_segment.raw_data
            sample_width = audio_segment.sample_width
            frame_rate = audio_segment.frame_rate
            channels = audio_segment.channels

            # Initialize PyAudio
            p = pyaudio.PyAudio()
            stream = p.open(
                format=p.get_format_from_width(sample_width),
                channels=channels,
                rate=frame_rate,
                output=True,
            )

            try:
                # Play audio data in chunks to allow stop signal
                chunk_size = 1024
                for i in range(0, len(raw_data), chunk_size):
                    if self._stop_speech.is_set():
                        logger.debug("Stop signal received, halting playback")
                        break

                    chunk = raw_data[i : i + chunk_size]
                    stream.write(chunk)

            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()

        except Exception as exc:
            logger.exception("Failed to play audio: %s", exc)
            raise TextToSpeechError("Failed to play audio") from exc


# Popular ElevenLabs voice IDs for easy reference
VOICE_IDS = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",  # Calm, clear (default)
    "domi": "AZnzlk1XvdvUeBnXmlld",  # Strong, confident
    "bella": "EXAVITQu4vr4xnSDxMaL",  # Soft, warm
    "antoni": "ErXwobaYiN019PkySvjV",  # Well-rounded male
    "elli": "MF3mGyEYCl7XYWbV9V6O",  # Emotional, expressive
    "josh": "TxGEqnHWrfWFTfGW9XjX",  # Deep, authoritative male
    "arnold": "VR6AewLTigWG4xSOukaG",  # Crisp, professional male
    "adam": "pNInz6obpgDQGcFmaJgB",  # Deep, narrator male
    "sam": "yoZ06aMxZJJ28mfd3POQ",  # Raspy, dynamic male
}


__all__ = ["ElevenLabsMCPTTS", "TextToSpeechError", "VOICE_IDS"]
