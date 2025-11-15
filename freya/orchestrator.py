"""Main conversation loop orchestrator."""

from __future__ import annotations

import queue
import re
import string
import threading
import time
from difflib import SequenceMatcher
from enum import Enum

from typing import Callable, List, Optional, Sequence

try:  # pragma: no cover - optional dependency for colored output
    from colorama import Fore, Style, init as colorama_init
except ImportError:  # pragma: no cover - runtime optional
    Fore = None  # type: ignore[assignment]
    Style = None  # type: ignore[assignment]
    colorama_init = None  # type: ignore[assignment]
else:  # pragma: no cover - side effect only when available
    colorama_init(autoreset=True)

try:  # pragma: no cover - optional hotkey dependency
    import keyboard
except ImportError:  # pragma: no cover - hotkey functionality is optional
    keyboard = None  # type: ignore[assignment]

_BLUE = getattr(Fore, "BLUE", "")
_GREEN = getattr(Fore, "GREEN", "")
_RESET = getattr(Style, "RESET_ALL", "")

_DEFAULT_MEMORY_KEYWORDS: Sequence[str] = (
    "remember",
    "my name is",
    "call me",
    "i like",
    "i dislike",
    "favorite",
    "my name",
    "birthday",
)

from requests import RequestException

from .config import LongTermMemoryConfig
from .context import ConversationContext
from .memory import MemoryRecord, PersistentMemoryStore
from .ollama_client import (
    OllamaClient,
    OllamaModelNotFoundError,
    OllamaStreamNotSupported,
)
from .logger import get_logger
from .stt import SpeechToText, SpeechToTextError
from .tts import TextToSpeech, TextToSpeechError
from .wake import WakeWordDetector, WakeWordDetectorError

logger = get_logger("orchestrator")


class InteractionMode(Enum):
    """Supported interaction channels for Freya."""

    VOICE = "voice"
    TEXT = "text"

    @classmethod
    def from_string(cls, value: str | None) -> "InteractionMode":
        normalized = (value or "").strip().lower()
        for mode in cls:
            if mode.value == normalized:
                return mode
        return cls.VOICE


class Orchestrator:
    """Run the interactive Freya chat session."""

    def __init__(
        self,
        client: OllamaClient,
        context: ConversationContext,
        stt: SpeechToText,
        tts: TextToSpeech,
        output_fn: Callable[[str], None] = print,
        wake_word: str = "Hey, Freya",
        wake_sensitivity: float = 0.75,
        session_window: float = 8.0,
        memory_store: Optional[PersistentMemoryStore] = None,
        memory_config: Optional[LongTermMemoryConfig] = None,
        interaction_mode: str = "voice",
        mode_toggle_hotkey: str = "ctrl+t",
        wake_detector: Optional[WakeWordDetector] = None,
    ) -> None:
        self._client = client
        self._context = context
        self._stt = stt
        self._tts = tts
        self._output = output_fn
        self._memory_store = memory_store if memory_config and memory_store and memory_config.enabled else None
        self._memory_config = memory_config if memory_config and memory_config.enabled else None
        self._memory_keywords: Sequence[str] = self._initialise_memory_keywords(memory_config)
        self._mode_lock = threading.Lock()
        self._current_mode = InteractionMode.from_string(interaction_mode)
        self._mode_toggle_hotkey = mode_toggle_hotkey.strip()
        self._hotkey_handle: Optional[int] = None
        self._hotkey_available = keyboard is not None and bool(self._mode_toggle_hotkey)
        self._wake_detector = wake_detector
        normalized = wake_word.strip()
        if not normalized:
            raise ValueError("wake_word must be a non-empty string")
        self._wake_word_display = normalized
        sensitivity = max(0.0, min(1.0, wake_sensitivity))
        self._wake_sensitivity = sensitivity if sensitivity > 0 else 0.75
        self._session_window = max(0.0, session_window)
        self._session_active_until = 0.0
        base = normalized.lower()
        punctless = base.translate(str.maketrans("", "", string.punctuation))
        variants = {base, punctless, " ".join(punctless.split())}
        self._wake_word_variants = [
            variant for variant in sorted(variants, key=len, reverse=True) if variant
        ]
        if not self._wake_word_variants:
            raise ValueError("wake_word must contain alphanumeric characters")
        self._wake_word_token_variants: List[Sequence[str]] = [
            tuple(filter(None, variant.split())) for variant in self._wake_word_variants
        ]
        if not any(self._wake_word_token_variants):
            raise ValueError("wake_word must contain at least one spoken token")
        self._max_variant_tokens = max(len(tokens) for tokens in self._wake_word_token_variants)
        self._token_offset_limit = 2
        self._token_pattern = re.compile(r"[\w']+")

        self._voice_ready_prompt = (
            "Freya is ready. Say "
            f"{self._wake_word_display} followed by your message. "
            "Say exit or quit to stop the conversation."
        )

        preload = getattr(self._tts, "preload_phrase", None)
        if callable(preload):
            try:
                preload(self._voice_ready_prompt)
                preload("Goodbye!")
            except Exception as exc:  # pragma: no cover - defensive logging only
                logger.debug("Unable to preload common speech phrases: %s", exc)

    def run(self) -> None:
        self._register_mode_hotkey()
        try:
            self._announce_startup()
            while True:
                mode = self._get_mode()
                if mode is InteractionMode.VOICE:
                    if not self._voice_cycle():
                        break
                else:
                    if not self._text_cycle():
                        break
        except KeyboardInterrupt:
            self._output("\n[Interrupted] Shutting down Freya. Goodbye!")
        finally:
            self._unregister_mode_hotkey()


    def _announce_startup(self) -> None:
        speak = self._get_mode() is InteractionMode.VOICE
        self._announce_mode(speak=speak)
        if self._hotkey_available:
            self._output(
                f"Freya: Press {self._mode_toggle_hotkey} to toggle between voice and text modes at any time."
            )
        elif self._mode_toggle_hotkey and keyboard is None:
            logger.warning(
                "keyboard package not available; interaction mode hotkey '%s' is disabled",
                self._mode_toggle_hotkey,
            )


    def _announce_mode(self, speak: bool = False) -> None:
        mode = self._get_mode()
        if mode is InteractionMode.VOICE:
            message = (
                "Freya: Voice mode active. Say "
                f"'{self._wake_word_display}' followed by your message. "
                "Say 'exit' or 'quit' to stop the conversation."
            )
        else:
            message = (
                "Freya: Text mode active. Type your message and press Enter. "
                "Type 'exit' or 'quit' to stop the conversation."
            )
        self._output(message)

        if speak and mode is InteractionMode.VOICE:
            try:
                self._tts.speak(self._voice_ready_prompt)
            except TextToSpeechError:
                self._output("[Warning] Unable to initialize speech output. Check logs.")


    def _voice_cycle(self) -> bool:
        while True:
            if self._get_mode() is not InteractionMode.VOICE:
                return True

            now = time.monotonic()
            session_active = now < self._session_active_until

            if not session_active:
                if self._wake_detector is not None:
                    woke, remainder = self._wait_for_wake_word()
                    if self._get_mode() is not InteractionMode.VOICE:
                        return True
                    if woke:
                        if self._session_window > 0:
                            self._session_active_until = time.monotonic() + self._session_window
                        session_active = True
                        if remainder:
                            self._handle_user_content(remainder)
                            continue
                    if not session_active and self._wake_detector is not None:
                        # Continue waiting for the wake word when the detector is active.
                        continue

            self._output("Listening...")
            try:
                self._stt.play_prompt_tone()
            except SpeechToTextError:
                self._output("[Warning] Unable to play the listening tone. Check logs.")

            try:
                user_input = self._stt.listen()
            except SpeechToTextError:
                self._output("[Error] Could not understand microphone input. Check logs.")
                continue

            message = user_input.strip()
            if not message:
                self._output("[No speech detected]")
                continue

            lowered = message.lower()
            if lowered in {"exit", "quit"}:
                return self._handle_exit()

            now = time.monotonic()
            session_active = now < self._session_active_until
            detected, cutoff = self._detect_wake_word(message)

            if detected:
                if self._session_window > 0:
                    self._session_active_until = now + self._session_window
                content = message[cutoff:].lstrip(" ,.!?-:")
                if not content:
                    if self._session_window > 0:
                        self._output("[Wake word detected] Listening for your request...")
                        continue
                    self._output("[No message after wake word detected]")
                    continue
            else:
                if session_active:
                    content = message
                    if self._session_window > 0:
                        self._session_active_until = now + self._session_window
                else:
                    self._output(
                        f"[Wake word not detected] Please say '{self._wake_word_display}' before your message."
                    )
                    continue

            self._handle_user_content(content)
            continue


    def _text_cycle(self) -> bool:
        while True:
            if self._get_mode() is not InteractionMode.TEXT:
                return True

            try:
                user_input = input("You: ")
            except EOFError:
                return self._handle_exit()

            message = (user_input or "").strip()
            if not message:
                self._output("[No text entered]")
                continue

            lowered = message.lower()
            if lowered in {"exit", "quit"}:
                return self._handle_exit()

            self._handle_user_content(message)
            continue


    def _handle_user_content(self, content: str) -> None:
        user_line = f"You said: {content}"
        if _BLUE:
            user_line = f"{_BLUE}{user_line}{_RESET}"
        self._output(user_line)
        logger.info("User input: %s", content)
        self._context.add_user_message(content)

        try:
            payload = self._prepare_messages(content)
            response, streamed, stream_tts_ok = self._obtain_assistant_response(payload)
        except OllamaModelNotFoundError as exc:
            logger.error("Ollama model missing: %s", exc)
            self._output(f"[Error] {exc}")
            return
        except RequestException as exc:
            logger.exception("Failed to contact Ollama: %s", exc)
            self._output("[Error] Unable to reach Ollama. Check logs.")
            return
        except Exception as exc:  # pragma: no cover - safety
            logger.exception("Unexpected error: %s", exc)
            self._output("[Error] Something went wrong. Check logs.")
            return

        logger.info("Freya: %s", response)
        self._context.add_assistant_message(response)
        self._maybe_store_exchange(content, response)

        assistant_line = f"Freya: {response}"
        if _GREEN:
            assistant_line = f"{_GREEN}{assistant_line}{_RESET}"
        self._output(assistant_line)
        spoke_successfully = stream_tts_ok if streamed else False
        if not streamed:
            try:
                self._tts.speak(response)
            except TextToSpeechError:
                self._output("[Warning] Unable to speak the response. Check logs.")
            else:
                spoke_successfully = True

        if self._session_window > 0 and self._get_mode() is InteractionMode.VOICE:
            if spoke_successfully:
                self._session_active_until = time.monotonic() + self._session_window
            # Ensure the follow-up window remains open even if audio playback failed
            self._session_active_until = max(
                self._session_active_until,
                time.monotonic() + self._session_window,
            )

    def _obtain_assistant_response(
        self, messages: list[dict]
    ) -> tuple[str, bool, bool]:
        """Return the assistant reply and whether streaming was used."""

        try:
            response, tts_ok = self._stream_assistant_response(messages)
        except OllamaStreamNotSupported:
            response = self._client.chat(messages)
            return response, False, False

        return response, True, tts_ok

    def _stream_assistant_response(self, messages: list[dict]) -> tuple[str, bool]:
        """Stream Ollama output and play audio concurrently."""

        chunk_queue: "queue.Queue[Optional[str]]" = queue.Queue()
        collected: list[str] = []
        buffer = ""
        tts_error: Optional[str] = None

        def worker() -> None:
            nonlocal tts_error
            while True:
                item = chunk_queue.get()
                if item is None:
                    chunk_queue.task_done()
                    break
                try:
                    self._tts.speak(item)
                except TextToSpeechError as exc:
                    if tts_error is None:
                        tts_error = str(exc) or "tts-error"
                finally:
                    chunk_queue.task_done()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        try:
            for chunk in self._client.chat_stream(messages):
                if not chunk:
                    continue
                collected.append(chunk)
                buffer += chunk
                speakable, buffer = self._partition_speakable(buffer)
                for piece in speakable:
                    chunk_queue.put(piece)
        finally:
            # Flush any remaining buffered text after the stream completes.
            speakable, buffer = self._partition_speakable(buffer, force=True)
            for piece in speakable:
                chunk_queue.put(piece)
            chunk_queue.put(None)
            chunk_queue.join()
            thread.join()

        if tts_error is not None:
            self._output("[Warning] Unable to speak the response. Check logs.")

        return "".join(collected).strip(), tts_error is None

    def _partition_speakable(
        self, buffer: str, *, force: bool = False
    ) -> tuple[list[str], str]:
        """Split accumulated text into speakable chunks."""

        pieces: list[str] = []
        working = buffer
        while True:
            split_idx = self._find_sentence_break(working)
            if split_idx is None:
                break
            piece = working[:split_idx].strip()
            if piece:
                pieces.append(piece)
            working = working[split_idx:].lstrip()

        if force and working.strip():
            pieces.append(working.strip())
            working = ""
        elif not pieces and len(working) > 240:
            cutoff = working.rfind(" ")
            if cutoff <= 0:
                cutoff = len(working)
            piece = working[:cutoff].strip()
            if piece:
                pieces.append(piece)
                working = working[cutoff:].lstrip()

        return pieces, working

    def _find_sentence_break(self, text: str) -> Optional[int]:
        """Return the index after the next sentence boundary, if any."""

        newline_idx = text.find("\n")
        punct_idx: Optional[int] = None
        for idx, char in enumerate(text):
            if char in ".!?":
                next_idx = idx + 1
                next_char = text[next_idx] if next_idx < len(text) else ""
                if not next_char or next_char.isspace():
                    punct_idx = next_idx
                    break

        candidates = [
            idx
            for idx in (
                newline_idx if newline_idx != -1 else None,
                punct_idx,
            )
            if idx is not None
        ]
        if not candidates:
            return None

        split_idx = min(candidates)
        while split_idx < len(text) and text[split_idx].isspace():
            split_idx += 1
        return split_idx


    def _handle_exit(self) -> bool:
        goodbye = "Goodbye!"
        goodbye_line = goodbye
        if _GREEN:
            goodbye_line = f"{_GREEN}{goodbye_line}{_RESET}"
        self._output(goodbye_line)
        try:
            self._tts.speak(goodbye)
        except TextToSpeechError:
            self._output("[Warning] Unable to speak the goodbye message.")
        return False


    def _register_mode_hotkey(self) -> None:
        if not self._hotkey_available or keyboard is None:
            return
        try:
            self._hotkey_handle = keyboard.add_hotkey(self._mode_toggle_hotkey, self._toggle_mode)
            logger.info("Registered interaction mode hotkey: %s", self._mode_toggle_hotkey)
        except Exception as exc:  # pragma: no cover - depends on OS hooks
            logger.warning(
                "Failed to register mode toggle hotkey '%s': %s",
                self._mode_toggle_hotkey,
                exc,
            )
            self._hotkey_handle = None
            self._hotkey_available = False


    def _unregister_mode_hotkey(self) -> None:
        if self._hotkey_handle is None or keyboard is None:
            return
        try:
            keyboard.remove_hotkey(self._hotkey_handle)
        except Exception as exc:  # pragma: no cover - depends on OS hooks
            logger.debug("Failed to remove hotkey '%s': %s", self._mode_toggle_hotkey, exc)
        finally:
            self._hotkey_handle = None


    def _get_mode(self) -> InteractionMode:
        with self._mode_lock:
            return self._current_mode


    def _set_mode(self, mode: InteractionMode) -> None:
        with self._mode_lock:
            self._current_mode = mode
            if mode is not InteractionMode.VOICE:
                self._session_active_until = 0.0


    def _toggle_mode(self) -> None:
        current = self._get_mode()
        new_mode = InteractionMode.TEXT if current is InteractionMode.VOICE else InteractionMode.VOICE
        self._set_mode(new_mode)
        logger.info("Interaction mode switched to %s", new_mode.value)
        self._announce_mode(speak=False)

    def _detect_wake_word(self, message: str) -> tuple[bool, int]:
        """Return whether the wake word was heard and the index after it."""
        trimmed = message.lstrip()
        leading = len(message) - len(trimmed)
        if not trimmed:
            return False, 0

        tokens = []
        for match in self._token_pattern.finditer(trimmed):
            tokens.append(match)
            if len(tokens) >= self._max_variant_tokens + self._token_offset_limit:
                break

        if not tokens:
            return False, 0

        for variant_tokens in self._wake_word_token_variants:
            required = len(variant_tokens)
            if required == 0 or len(tokens) < required:
                continue
            max_offset = min(len(tokens) - required, self._token_offset_limit)
            for offset in range(max_offset + 1):
                candidate = tokens[offset : offset + required]
                normalized = [match.group().lower() for match in candidate]
                scores = [
                    SequenceMatcher(None, cand, variant_tokens[idx]).ratio()
                    for idx, cand in enumerate(normalized)
                ]
                average = sum(scores) / required if required else 0.0
                if average >= self._wake_sensitivity:
                    cutoff = candidate[-1].end()
                    return True, leading + cutoff

        return False, 0

    def _wait_for_wake_word(self) -> tuple[bool, str]:
        """Block on the lightweight detector until the wake word is heard."""

        detector = self._wake_detector
        if detector is None:
            return False, ""

        announced = False
        while (
            self._get_mode() is InteractionMode.VOICE
            and time.monotonic() >= self._session_active_until
        ):
            if not announced:
                self._output(f"Waiting for '{self._wake_word_display}'...")
                announced = True
            try:
                transcript = detector.listen_once()
            except WakeWordDetectorError as exc:
                logger.warning("Wake detector disabled after error: %s", exc)
                self._output(
                    "[Warning] Wake detector unavailable; falling back to full transcription."
                )
                self._wake_detector = None
                return False, ""

            if self._get_mode() is not InteractionMode.VOICE:
                return False, ""

            if not transcript:
                continue

            detected, cutoff = self._detect_wake_word(transcript)
            if detected:
                remainder = transcript[cutoff:].lstrip(" ,.!?-:")
                return True, remainder

        return False, ""


    def _initialise_memory_keywords(
        self, memory_config: Optional[LongTermMemoryConfig]
    ) -> Sequence[str]:
        if not memory_config or not memory_config.enabled:
            return ()
        configured = tuple(keyword for keyword in memory_config.auto_store_keywords if keyword)
        if configured:
            lower_keywords = tuple({keyword.lower() for keyword in configured if keyword.strip()})
        else:
            lower_keywords = ()
        return lower_keywords or _DEFAULT_MEMORY_KEYWORDS

    def _prepare_messages(self, user_text: str) -> List[dict]:
        base_messages = self._context.as_messages()
        if not base_messages or not self._memory_store or not self._memory_config:
            return base_messages

        try:
            matches = self._memory_store.find_similar_memories(
                user_text,
                limit=self._memory_config.recall_limit,
                min_score=self._memory_config.min_similarity,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to retrieve memories: %s", exc)
            return base_messages

        if not matches:
            return base_messages

        memory_block = self._format_memory_block(matches)
        enriched_messages = [base_messages[0], {"role": "system", "content": memory_block}]
        enriched_messages.extend(base_messages[1:])
        logger.debug("Injected %s memory snippets into prompt", len(matches))
        return enriched_messages

    @staticmethod
    def _format_memory_block(matches: Sequence[MemoryRecord]) -> str:
        lines = ["Relevant prior memories:"]
        for match in matches:
            snippet = match.content.strip()
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            lines.append(f"- ({match.role}) {snippet}")
        return "\n".join(lines)

    def _maybe_store_exchange(self, user_text: str, assistant_text: str) -> None:
        if not self._memory_store or not self._memory_config:
            return

        keyword = self._match_memory_keyword(user_text)
        if not keyword:
            logger.debug("User message did not match memory keywords; skipping store")
            return

        metadata = {"source": "user", "keyword": keyword}
        importance = 2

        try:
            self._memory_store.store_memory(
                content=user_text,
                role="user",
                importance=importance,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to store user memory: %s", exc)

        if not self._memory_config.store_assistant_messages:
            return

        assistant_text = (assistant_text or "").strip()
        if not assistant_text:
            return

        try:
            self._memory_store.store_memory(
                content=assistant_text,
                role="assistant",
                importance=1,
                metadata={"source": "assistant"},
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to store assistant memory: %s", exc)

    def _match_memory_keyword(self, text: str) -> Optional[str]:
        lowered = (text or "").strip().lower()
        if not lowered:
            return None
        for keyword in self._memory_keywords:
            if keyword and keyword in lowered:
                return keyword
        return None


__all__ = ["Orchestrator"]