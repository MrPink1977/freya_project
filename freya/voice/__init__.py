"""Voice module - speech-to-text, text-to-speech, wake word detection."""

from freya.voice.stt import SpeechToText, SpeechToTextError
from freya.voice.tts import TextToSpeech, TextToSpeechError
from freya.voice.wake import WakeWordDetector, WakeWordDetectorError
from freya.voice.wake_word_matcher import WakeWordMatcher

__all__ = [
    "SpeechToText",
    "SpeechToTextError",
    "TextToSpeech",
    "TextToSpeechError",
    "WakeWordDetector",
    "WakeWordDetectorError",
    "WakeWordMatcher",
]
