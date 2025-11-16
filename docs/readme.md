 Freya (Phase 1) – Local Voice Chatbot

Freya is a locally hosted conversational AI assistant powered by [Ollama](https://ollama.ai/).
Phase 1 now supports fully voice-driven conversations: speak to Freya, she transcribes your
words with Whisper, generates a response with Ollama, and replies aloud via text-to-speech.

## ✨ Features

- 📁 Structured Python project with clear separation of concerns
- ⚙️ YAML configuration loader with environment overrides
- 🪵 Centralized logging for debugging and observability
- 💬 Conversation context manager with optional summarisation of older turns
- 🤖 Ollama API client for sending prompts and receiving responses
- 🎙️ Whisper-powered speech-to-text with automatic silence detection
- 🔊 Offline text-to-speech powered by Piper + PyAudio
- 🧠 Short-term contextual memory plus persistent SQLite-backed recall
- 🎚️ Hotkey toggle between voice capture and keyboard-driven text mode

## 🚀 Getting Started

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Voice dependencies:** The speech pipeline uses `sounddevice`/`soundfile` for
> microphone capture, Piper for text-to-speech synthesis, and `pyaudio` for playback. If
> any are missing, Freya will display actionable diagnostics before starting the chat
> loop so you can install the required packages or fall back to text-only mode.

Common installation tips:

- **Linux:** `sudo apt-get install python3-dev portaudio19-dev` before installing the
  Python requirements.
- **macOS:** `brew install portaudio ffmpeg` if the default wheels fail.
- **Windows:** Install the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  and ensure you use a 64-bit Python environment. `pip install sounddevice soundfile pyttsx3`.

> **Note:** Whisper requires PyTorch. Install the build appropriate for your platform before
> installing the Python dependencies if `pip` does not handle it automatically.

### 2. Run Ollama Locally

Install and start Ollama, then pull the model referenced in `config/default.yaml` (default: `llama3`).

```bash
ollama pull llama3
ollama serve
```

### 3. Configure Freya (Optional)

Edit `config/default.yaml` or create a custom config and point to it via the `FREYA_CONFIG`
environment variable.

```bash
export FREYA_CONFIG=/path/to/custom.yaml
```

Key configuration groups:

- `ollama`: Host, model, and generation options for Ollama.
- `app`: System prompt (max history is now derived from the memory configuration).
- `app`: System prompt, wake-word sensitivity, default interaction mode, and the voice/text toggle hotkey.
- `stt`: Whisper model, microphone sample rate, silence detection thresholds, and
  device selection (`auto` by default tries CUDA first, then falls back to CPU).
- `tts`: Piper ONNX voice path used for spoken responses.
- `memory`: Short-term history limits, summarisation toggles, and long-term storage
  options (database path, similarity thresholds, keywords to capture, etc.).

### 4. Start Talking

```bash
python main.py
```

You will hear a short tone to indicate the microphone is recording. Speak naturally; say "exit"
or "quit" to end the session. Responses are spoken aloud and also printed to the console for
reference.
or "quit" to end the session. Need to fall back to typing? Press the configured hotkey (default
`Ctrl+T`) to switch into text mode instantly, then type your prompt at the `You:` prompt. Press the
same hotkey again to jump back to voice input. Responses are spoken aloud and also printed to the
console for reference.

## 🧱 Project Structure

```
freya/
  config.py         # YAML settings loader
  context.py        # Rolling conversation history manager
  logger.py         # Logging helpers
  memory.py         # Persistent long-term memory store
  ollama_client.py  # Ollama HTTP API wrapper
  orchestrator.py   # Voice conversation loop
  stt.py            # Whisper microphone capture and transcription
  tts.py            # Text-to-speech playback
config/
  default.yaml      # Default application + Ollama + voice configuration
main.py             # Application entry point
requirements.txt    # Python dependencies
```

## 🛠️ Next Steps

Future phases will build on this foundation to add:

- 🧭 Richer semantic embeddings for long-term memory retrieval
- 👁️ Computer vision integration
