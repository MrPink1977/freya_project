"""Simple TTS test - just speaks immediately."""

import sys
from pathlib import Path

from freya.config import load_settings
from freya.tts import TextToSpeech

print("Loading config...")
config = load_settings(Path("config/default.yaml"))

print(f"TTS Engine: {config.tts.engine}")
print(f"Voice: {config.tts.voice_path}")
print("\nSpeaking with Piper...")

tts = TextToSpeech(config.tts)
tts.speak("Hello! I am Freya. Testing audio output.")
tts.close()

print("Done! Did you hear me?")
