import sys
import types
import unittest
from typing import List, Tuple

# Provide minimal stubs for optional third-party dependencies so the orchestrator
# module can be imported in a lean test environment.
_requests_stub = types.ModuleType("requests")


class _RequestExceptionStub(Exception):
    pass


class _HTTPErrorStub(_RequestExceptionStub):
    def __init__(self, message="", response=None):
        super().__init__(message)
        self.response = response


class _ResponseStub:  # pragma: no cover - simple container
    def __init__(self):
        self.status_code = 200

    def json(self):
        return {}

    @property
    def text(self):
        return ""


class _SessionStub:  # pragma: no cover - not exercised in tests
    def post(self, *args, **kwargs):
        raise NotImplementedError


_requests_stub.RequestException = _RequestExceptionStub
_requests_stub.HTTPError = _HTTPErrorStub
_requests_stub.Response = _ResponseStub
_requests_stub.Session = _SessionStub
sys.modules.setdefault("requests", _requests_stub)

_yaml_stub = types.ModuleType("yaml")
_yaml_stub.safe_load = lambda handle: {}
sys.modules.setdefault("yaml", _yaml_stub)

# Stub out heavy runtime modules that aren't needed for these unit tests.
stt_stub = types.ModuleType("freya.stt")


class _SpeechToText:  # pragma: no cover - placeholder for type references
    pass


class _SpeechToTextError(Exception):
    pass


stt_stub.SpeechToText = _SpeechToText
stt_stub.SpeechToTextError = _SpeechToTextError
sys.modules.setdefault("freya.stt", stt_stub)

tts_stub = types.ModuleType("freya.tts")


class _TextToSpeech:  # pragma: no cover - placeholder for type references
    pass


class _TextToSpeechError(Exception):
    pass


tts_stub.TextToSpeech = _TextToSpeech
tts_stub.TextToSpeechError = _TextToSpeechError
sys.modules.setdefault("freya.tts", tts_stub)

wake_stub = types.ModuleType("freya.wake")


class _WakeWordDetector:  # pragma: no cover - placeholder for type references
    def __init__(self, *args, **kwargs):
        pass

    def listen_once(self):
        return ""


class _WakeWordDetectorError(Exception):
    pass


wake_stub.WakeWordDetector = _WakeWordDetector
wake_stub.WakeWordDetectorError = _WakeWordDetectorError
sys.modules.setdefault("freya.wake", wake_stub)

from freya.context import ConversationContext
from freya.orchestrator import InteractionMode, Orchestrator


class _KeyboardStub:
    def __init__(self) -> None:
        self.added: List[Tuple[str, object]] = []
        self.removed: List[int] = []

    def add_hotkey(self, combo: str, callback):
        self.added.append((combo, callback))
        # use a deterministic handle value
        return len(self.added)

    def remove_hotkey(self, handle: int) -> None:
        self.removed.append(handle)


class _DummyClient:
    def chat(self, messages):  # pragma: no cover - not exercised
        return "ok"


class _DummySTT:
    def play_prompt_tone(self):  # pragma: no cover - not exercised
        pass

    def listen(self):  # pragma: no cover - not exercised
        return "exit"


class _DummyTTS:
    def speak(self, text: str):  # pragma: no cover - not exercised
        pass


class OrchestratorHotkeyTests(unittest.TestCase):
    def setUp(self) -> None:
        import freya.orchestrator as orch_mod

        self._orch_mod = orch_mod
        self._original_keyboard = orch_mod.keyboard
        self._keyboard_stub = _KeyboardStub()
        orch_mod.keyboard = self._keyboard_stub

    def tearDown(self) -> None:
        self._orch_mod.keyboard = self._original_keyboard

    def _build_orchestrator(self, interaction_mode: str = "voice") -> Orchestrator:
        context = ConversationContext(system_prompt="Test", max_history=3)
        return Orchestrator(
            client=_DummyClient(),
            context=context,
            stt=_DummySTT(),
            tts=_DummyTTS(),
            output_fn=lambda _: None,
            wake_word="Hey, Freya",
            wake_sensitivity=0.8,
            session_window=5.0,
            interaction_mode=interaction_mode,
            mode_toggle_hotkey="ctrl+alt+m",
        )

    def test_hotkey_registration_and_toggle(self) -> None:
        orchestrator = self._build_orchestrator()

        # registering the hotkey should store the combo on the stub
        orchestrator._register_mode_hotkey()
        self.assertTrue(self._keyboard_stub.added)
        combo, callback = self._keyboard_stub.added[0]
        self.assertEqual(combo, "ctrl+alt+m")
        self.assertEqual(orchestrator._get_mode(), InteractionMode.VOICE)

        # invoking the callback should toggle between voice and text
        callback()
        self.assertEqual(orchestrator._get_mode(), InteractionMode.TEXT)
        callback()
        self.assertEqual(orchestrator._get_mode(), InteractionMode.VOICE)

        # unregister should remove the handle we were given
        orchestrator._unregister_mode_hotkey()
        self.assertIn(1, self._keyboard_stub.removed)

    def test_toggle_mode_manual(self) -> None:
        orchestrator = self._build_orchestrator(interaction_mode="text")
        self.assertEqual(orchestrator._get_mode(), InteractionMode.TEXT)

        orchestrator._toggle_mode()
        self.assertEqual(orchestrator._get_mode(), InteractionMode.VOICE)

        orchestrator._toggle_mode()
        self.assertEqual(orchestrator._get_mode(), InteractionMode.TEXT)


if __name__ == "__main__":
    unittest.main()