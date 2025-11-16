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

from requests import RequestException

from .config import LongTermMemoryConfig
from .context import ConversationContext
from .logger import get_logger
from .memory import MemoryRecord, PersistentMemoryStore
from .ollama_client import (
    OllamaClient,
    OllamaModelNotFoundError,
    OllamaStreamNotSupported,
)
from .stt import SpeechToText, SpeechToTextError
from .tools.web_search import search_web, WebSearchError
from .tts import TextToSpeech, TextToSpeechError
from .wake import WakeWordDetector, WakeWordDetectorError

logger = get_logger("orchestrator")

_BLUE = getattr(Fore, "BLUE", "")
_GREEN = getattr(Fore, "GREEN", "")
_RESET = getattr(Style, "RESET_ALL", "")


def _strip_markdown_for_speech(text: str) -> str:
    """Remove markdown formatting from text before TTS.

    Removes:
    - Bold/italic markers: **, *, _
    - Code blocks: ```
    - Inline code: `
    - Links: [text](url) -> text
    - Parenthetical asides in conversational text
    """
    if not text:
        return text

    # Remove code blocks first
    cleaned = re.sub(r"```[\s\S]*?```", "", text)

    # Remove inline code
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # Remove bold/italic markers
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)

    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

    # Remove extra parenthetical asides that sound awkward when spoken
    # Only remove if they look like clarifications/metadata
    cleaned = re.sub(r"\s*\([A-Z][^)]{0,30}\)\s*", " ", cleaned)

    # Clean up multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


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

_WEB_SEARCH_TRIGGERS: Sequence[str] = (
    "search",
    "search for",
    "look up",
    "find information about",
    "what is",
    "who is",
    "when did",
    "where is",
    "how many",
    "tell me about",
    "find out",
)


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
        self._stop_speech_hotkey_handle: Optional[int] = None
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
        self._wake_word_variants = [variant for variant in sorted(variants, key=len, reverse=True) if variant]
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
        self._register_stop_speech_hotkey()
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
            self._unregister_stop_speech_hotkey()

    def _announce_startup(self) -> None:
        speak = self._get_mode() is InteractionMode.VOICE
        self._announce_mode(speak=speak)
        if self._hotkey_available:
            self._output(f"Freya: Press {self._mode_toggle_hotkey} to toggle between voice and text modes at any time.")
            self._output("Freya: Press SPACE to stop Freya from speaking.")
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
                self._tts.speak(_strip_markdown_for_speech(self._voice_ready_prompt))
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

        # Extract and store any facts from user input
        try:
            self._extract_and_store_facts(content)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to extract facts: %s", exc)

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
        if not streamed:
            try:
                self._tts.speak(_strip_markdown_for_speech(response))
            except TextToSpeechError:
                self._output("[Warning] Unable to speak the response. Check logs.")

        if self._session_window > 0 and self._get_mode() is InteractionMode.VOICE:
            # Extend session window after assistant response to allow follow-up questions
            self._session_active_until = time.monotonic() + self._session_window

    def _obtain_assistant_response(self, messages: list[dict]) -> tuple[str, bool, bool]:
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
                    self._tts.speak(_strip_markdown_for_speech(item))
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

    def _partition_speakable(self, buffer: str, *, force: bool = False) -> tuple[list[str], str]:
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
            self._tts.speak(_strip_markdown_for_speech(goodbye))
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

    def _register_stop_speech_hotkey(self) -> None:
        """Register the space bar hotkey to stop speech playback."""
        if keyboard is None:
            return
        try:
            self._stop_speech_hotkey_handle = keyboard.add_hotkey("space", self._stop_speech)
            logger.info("Registered stop speech hotkey: SPACE")
        except Exception as exc:  # pragma: no cover - depends on OS hooks
            logger.warning("Failed to register stop speech hotkey: %s", exc)
            self._stop_speech_hotkey_handle = None

    def _unregister_stop_speech_hotkey(self) -> None:
        """Unregister the stop speech hotkey."""
        if self._stop_speech_hotkey_handle is None or keyboard is None:
            return
        try:
            keyboard.remove_hotkey(self._stop_speech_hotkey_handle)
        except Exception as exc:  # pragma: no cover - depends on OS hooks
            logger.debug("Failed to remove stop speech hotkey: %s", exc)
        finally:
            self._stop_speech_hotkey_handle = None

    def _stop_speech(self) -> None:
        """Stop current TTS playback."""
        logger.info("Stop speech hotkey pressed")
        self._tts.stop_speaking()

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
                    SequenceMatcher(None, cand, variant_tokens[idx]).ratio() for idx, cand in enumerate(normalized)
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
        while self._get_mode() is InteractionMode.VOICE and time.monotonic() >= self._session_active_until:
            if not announced:
                self._output(f"Waiting for '{self._wake_word_display}'...")
                announced = True
            try:
                transcript = detector.listen_once()
            except WakeWordDetectorError as exc:
                logger.warning("Wake detector disabled after error: %s", exc)
                self._output("[Warning] Wake detector unavailable; falling back to full transcription.")
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

    def _initialise_memory_keywords(self, memory_config: Optional[LongTermMemoryConfig]) -> Sequence[str]:
        if not memory_config or not memory_config.enabled:
            return ()
        configured = tuple(keyword for keyword in memory_config.auto_store_keywords if keyword)
        if configured:
            lower_keywords = tuple({keyword.lower() for keyword in configured if keyword.strip()})
        else:
            lower_keywords = ()
        return lower_keywords or _DEFAULT_MEMORY_KEYWORDS

    def _maybe_search_web(self, user_text: str) -> Optional[str]:
        """Check if the query needs web search and perform it if needed.

        Returns:
            Formatted search results as a string, or None if search not needed/failed
        """
        lowered = user_text.lower().strip()

        # Check if any search trigger is present
        needs_search = any(trigger in lowered for trigger in _WEB_SEARCH_TRIGGERS)

        if not needs_search:
            return None

        # Smart query extraction - extract meaningful search terms
        search_query = self._extract_search_query(user_text, lowered)

        if not search_query:
            return None

        try:
            logger.info("Performing web search for: %s", search_query)
            self._output(f"[Searching the web for: {search_query}]")
            results = search_web(search_query, max_results=3)

            if results and "No search results" not in results:
                formatted = (
                    f"WEB SEARCH RESULTS for '{search_query}':\n{results}\n\n"
                    "You have web search capability. Use the above current information "
                    "to answer the user's question accurately."
                )
                logger.debug("Web search successful, %d chars returned", len(results))
                return formatted

        except WebSearchError as exc:
            logger.warning("Web search failed: %s", exc)
            self._output(f"[Web search unavailable: {exc}]")
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Unexpected web search error: %s", exc)

        return None

    def _extract_search_query(self, user_text: str, lowered: str) -> Optional[str]:
        """Extract the actual search query from user input.

        Handles conversational input like:
        - "search for Python tutorials"
        - "I want to hear the news from today, search the internet"
        - "what is machine learning"
        """
        # Remove common conversational filler at start
        conversational_prefixes = [
            "no, ",
            "yes, ",
            "ok, ",
            "okay, ",
            "sure, ",
            "alright, ",
            "i want to ",
            "i'd like to ",
            "i need to ",
            "can you ",
            "could you ",
            "please ",
            "will you ",
        ]

        cleaned = lowered
        for prefix in conversational_prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()

        # Find which trigger was used and its position
        trigger_found = None
        trigger_pos = -1
        for trigger in _WEB_SEARCH_TRIGGERS:
            pos = cleaned.find(trigger)
            if pos >= 0:
                trigger_found = trigger
                trigger_pos = pos
                break

        if not trigger_found:
            return None

        # Extract query based on trigger position
        if trigger_pos == 0:
            # Trigger at start: "search for X" or "what is X"
            query = cleaned[len(trigger_found) :].strip()
            # Remove common connecting words
            for connector in ["for", "about", "on", "the", "a", "an"]:
                if query.startswith(connector + " "):
                    query = query[len(connector) + 1 :].strip()
        else:
            # Trigger in middle/end: "hear the news from today, search the internet"
            # Extract the topic before the trigger
            before_trigger = cleaned[:trigger_pos].strip()

            # Remove trailing punctuation and connectors
            before_trigger = before_trigger.rstrip(",.!?;:")

            # Extract key phrases
            if "news" in before_trigger:
                # Extract news-related query
                if "from today" in before_trigger or "today's" in before_trigger:
                    query = "today's news"
                elif "from yesterday" in before_trigger or "yesterday's" in before_trigger:
                    query = "yesterday's news"
                else:
                    query = "news"
            elif "weather" in before_trigger:
                query = "weather"
                # Could add location extraction here
            else:
                # Use last meaningful phrase before trigger
                words = before_trigger.split()
                # Get last 3-5 words as query
                query = " ".join(words[-min(5, len(words)) :])

        # Final cleanup - remove trailing questions and phrases
        query = query.strip()

        # Remove common trailing questions/phrases that don't belong in search queries
        trailing_patterns = [
            r"\s+and tell me .*$",
            r"\s+and let me know .*$",
            r"\s+and find out .*$",
            r"\s+and see .*$",
            r"\s+please$",
            r"\s+thanks?$",
            r"\s+thank you$",
        ]
        for pattern in trailing_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        query = query.strip()
        if not query or len(query) < 2:
            return None

        return query

    def _extract_and_store_facts(self, user_text: str) -> None:
        """Extract and store structured facts from user input."""
        if not self._memory_store:
            return

        lowered = user_text.lower().strip()

        # Skip extraction from questions - they're asking, not telling
        question_indicators = [
            "do you",
            "can you",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "is it",
            "are you",
            "will you",
            "should",
            "could",
            "would",
            "remember my",
            "know my",
            "recall",
        ]
        if any(lowered.startswith(indicator) or f" {indicator}" in lowered for indicator in question_indicators):
            logger.debug("Skipping fact extraction - detected question")
            return

        # Extract name - improved patterns
        # Pattern 1: "my name is X" or "my name's X"
        match = re.search(r"my name(?:'s| is) (\w+(?:\s+\w+)?)", lowered)
        if match:
            name = match.group(1).strip().title()
            # Validate it's actually a name (not a number, not too short)
            if len(name) >= 2 and not name.isdigit():
                try:
                    self._memory_store.store_fact(category="name", key="name", value=name)
                    logger.info("Extracted fact: name.name = '%s'", name)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Pattern 2: "call me X" or "you can call me X"
        match = re.search(r"(?:you can |just )?call me (\w+)", lowered)
        if match:
            name = match.group(1).strip().title()
            if len(name) >= 2 and not name.isdigit() and name.lower() not in ["back", "later", "tomorrow"]:
                try:
                    self._memory_store.store_fact(category="name", key="name", value=name)
                    logger.info("Extracted fact: name.name = '%s'", name)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Extract birthday - improved patterns
        # Pattern 1: "my birthday is Month Day, Year" or "my birthday is Month Day"
        match = re.search(r"my birthday(?:'s| is) ([a-z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?)", lowered)
        if match:
            birthday = match.group(1).strip().title()
            try:
                self._memory_store.store_fact(category="birthday", key="birthday", value=birthday)
                logger.info("Extracted fact: birthday.birthday = '%s'", birthday)
            except Exception as exc:
                logger.warning("Failed to store fact: %s", exc)
            return

        # Pattern 2: "I was born in/on Month Day, Year" or "born in Year"
        match = re.search(
            r"(?:i was )?born (?:on |in )?([a-z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?|\d{4}|[a-z]+ \d{4})", lowered
        )
        if match:
            birthday = match.group(1).strip().title()
            # Don't extract if it's a question word like "in?"
            if not birthday.endswith("?") and len(birthday) >= 4:
                try:
                    self._memory_store.store_fact(category="birthday", key="birthday", value=birthday)
                    logger.info("Extracted fact: birthday.birthday = '%s'", birthday)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Extract likes - improved patterns
        # Pattern 1: "I like X" (but not "I like to")
        match = re.search(r"i (?:really |absolutely )?like ([a-z]+(?:\s+[a-z]+)?)", lowered)
        if match:
            thing = match.group(1).strip()
            # Filter out common false positives
            if thing not in ["to", "that", "this", "it", "how", "when", "where"] and len(thing) >= 3:
                key = thing.split()[0]
                try:
                    self._memory_store.store_fact(category="likes", key=key, value=thing)
                    logger.info("Extracted fact: likes.%s = '%s'", key, thing)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Pattern 2: "I love X"
        match = re.search(r"i love ([a-z]+(?:\s+[a-z]+)?)", lowered)
        if match:
            thing = match.group(1).strip()
            if thing not in ["to", "that", "this", "it", "how", "when", "where"] and len(thing) >= 3:
                key = thing.split()[0]
                try:
                    self._memory_store.store_fact(category="likes", key=key, value=thing)
                    logger.info("Extracted fact: likes.%s = '%s'", key, thing)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Pattern 3: "I enjoy X"
        match = re.search(r"i enjoy ([a-z]+(?:\s+[a-z]+)?)", lowered)
        if match:
            thing = match.group(1).strip()
            if len(thing) >= 3:
                key = thing.split()[0]
                try:
                    self._memory_store.store_fact(category="likes", key=key, value=thing)
                    logger.info("Extracted fact: likes.%s = '%s'", key, thing)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Extract dislikes
        # Pattern 1: "I don't like X"
        match = re.search(r"i (?:don't|do not|dont) like ([a-z]+(?:\s+[a-z]+)?)", lowered)
        if match:
            thing = match.group(1).strip()
            if thing not in ["to", "that", "this", "it", "how", "when", "where"] and len(thing) >= 3:
                key = thing.split()[0]
                try:
                    self._memory_store.store_fact(category="dislikes", key=key, value=thing)
                    logger.info("Extracted fact: dislikes.%s = '%s'", key, thing)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Pattern 2: "I hate X"
        match = re.search(r"i hate ([a-z]+(?:\s+[a-z]+)?)", lowered)
        if match:
            thing = match.group(1).strip()
            if len(thing) >= 3:
                key = thing.split()[0]
                try:
                    self._memory_store.store_fact(category="dislikes", key=key, value=thing)
                    logger.info("Extracted fact: dislikes.%s = '%s'", key, thing)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

        # Pattern 3: "I dislike X"
        match = re.search(r"i dislike ([a-z]+(?:\s+[a-z]+)?)", lowered)
        if match:
            thing = match.group(1).strip()
            if len(thing) >= 3:
                key = thing.split()[0]
                try:
                    self._memory_store.store_fact(category="dislikes", key=key, value=thing)
                    logger.info("Extracted fact: dislikes.%s = '%s'", key, thing)
                except Exception as exc:
                    logger.warning("Failed to store fact: %s", exc)
                return

    def _retrieve_facts(self, query: str) -> Optional[str]:
        """Check if query is asking for a fact and retrieve it."""
        if not self._memory_store:
            return None

        lowered = query.lower()

        # Check for name queries
        if any(phrase in lowered for phrase in ["my name", "what's my name", "who am i", "do you know my name"]):
            fact = self._memory_store.get_fact("name", "name")
            if fact:
                return f"FACT: Your name is {fact.value}."

        # Check for birthday queries
        if any(phrase in lowered for phrase in ["my birthday", "when was i born", "when am i born", "my birth"]):
            fact = self._memory_store.get_fact("birthday", "birthday")
            if fact:
                return f"FACT: Your birthday is {fact.value}."

        # Check for likes queries
        if any(phrase in lowered for phrase in ["what do i like", "things i like", "my favorite", "do i like"]):
            facts = self._memory_store.get_fact("likes")
            if isinstance(facts, list) and facts:
                likes_list = [f.value for f in facts[:3]]  # Top 3
                return f"FACT: You like: {', '.join(likes_list)}."

        # Check for dislikes queries
        if any(
            phrase in lowered for phrase in ["what do i dislike", "what don't i like", "things i hate", "do i dislike"]
        ):
            facts = self._memory_store.get_fact("dislikes")
            if isinstance(facts, list) and facts:
                dislikes_list = [f.value for f in facts[:3]]
                return f"FACT: You dislike: {', '.join(dislikes_list)}."

        return None

    def _prepare_messages(self, user_text: str) -> List[dict]:
        base_messages = self._context.as_messages()

        # Check if web search is needed
        search_results = self._maybe_search_web(user_text)

        # Check for structured facts first (instant lookup)
        facts_block: Optional[str] = None
        if self._memory_store and self._memory_config:
            try:
                facts_block = self._retrieve_facts(user_text)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Failed to retrieve facts: %s", exc)

        # Retrieve relevant semantic memories
        memory_block: Optional[str] = None
        if self._memory_store and self._memory_config and not facts_block:
            # Only do semantic search if facts didn't answer the question
            try:
                matches = self._memory_store.find_similar_memories(
                    user_text,
                    limit=self._memory_config.recall_limit,
                    min_score=self._memory_config.min_similarity,
                )
                if matches:
                    memory_block = self._format_memory_block(matches)
                    logger.debug("Injected %s memory snippets into prompt", len(matches))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Failed to retrieve memories: %s", exc)

        # Build enriched message list with search results, facts, and/or memories
        if not search_results and not facts_block and not memory_block:
            return base_messages

        enriched_messages = [base_messages[0]]  # Start with system prompt

        if search_results:
            enriched_messages.append({"role": "system", "content": search_results})

        if facts_block:
            enriched_messages.append({"role": "system", "content": facts_block})

        if memory_block:
            enriched_messages.append({"role": "system", "content": memory_block})

        enriched_messages.extend(base_messages[1:])  # Add conversation history
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
