# Freya - Voice-Enabled AI Assistant

Freya is a sophisticated voice-enabled AI assistant with computer vision capabilities. It combines speech recognition, natural language processing via Ollama, and camera integration to create an interactive, context-aware assistant.

## Features

### Core Voice Assistant
- **Speech-to-Text**: Uses Faster Whisper for accurate speech recognition
- **Text-to-Speech**: Piper TTS for natural-sounding voice synthesis
- **Wake Word Detection**: Hands-free activation with configurable wake words
- **Conversation Memory**: Short-term context management with automatic summarization
- **Persistent Storage**: Long-term memory using SQLite with semantic search

### Vision Capabilities
- **Facial Recognition**: Identify known individuals using face_recognition library
- **RTSP Camera Integration**: Connect to IP cameras for video streaming
- **ONVIF Support**: Control cameras that support ONVIF protocol
- **Multi-Channel Audio**: Coordinate audio from multiple sources (mic + cameras)

### AI Integration
- **Ollama Backend**: Flexible LLM integration supporting various models
- **Web Search Tool**: DuckDuckGo integration for real-time information
- **Streaming Responses**: Real-time text-to-speech streaming during generation

### Interaction Modes
- **Voice Mode**: Hands-free conversation with wake word detection
- **Push-to-Talk**: Press-and-hold for voice input
- **Hotkey Toggle**: Switch between modes on the fly

## Requirements

- Python 3.11+
- Ollama (running locally or remotely)
- Audio input device (microphone)
- Audio output device (speakers)

### Optional Requirements
- IP Camera with RTSP support (for vision features)
- face_recognition library and dlib (for facial recognition)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/MrPink1977/freya_project.git
cd freya_project
```

### 2. Install Dependencies
```bash
# Basic installation
pip install -r requirements.txt

# Or install as a package with dev tools
pip install -e ".[dev]"

# For facial recognition (optional)
pip install -e ".[face-recognition]"
```

### 3. Install Ollama
Download and install Ollama from [ollama.ai](https://ollama.ai)

```bash
# Pull a model (e.g., llama2)
ollama pull llama2
```

### 4. Configure Freya
Copy the default configuration and customize it:

```bash
cp config/default.yaml config/my_config.yaml
# Edit my_config.yaml with your settings
```

Key configuration sections:
- **Ollama**: Model selection and host configuration
- **Audio**: Microphone and speaker device selection
- **Wake Word**: Sensitivity and activation settings
- **Memory**: Long-term storage paths and settings
- **Vision**: Camera credentials and facial recognition setup

## Usage

### Basic Usage
```bash
# Run with default configuration
python main.py

# Run with custom config
python main.py --config config/my_config.yaml

# Run in diagnostic mode (shows detailed logs)
python main.py --startup-mode diagnostic
```

### Facial Recognition Setup
1. Create a directory structure for known faces:
```bash
mkdir -p data/faces/PersonName
```

2. Add photos of the person (one face per image):
```bash
cp photo.jpg data/faces/PersonName/
```

3. Enable facial recognition in your config:
```yaml
vision:
  facial_recognition:
    enabled: true
    faces_directory: "data/faces"
```

### Camera Integration
Configure your camera in the config file:

```yaml
channels:
  - channel_id: "camera_main"
    channel_type: "reolink"
    enabled: true
    ip: "192.168.0.22"
    rtsp_port: 554
    username: "admin"
    password: "your_password"
```

## Configuration

### Environment Variables
- `FREYA_STARTUP_MODE`: Set to `normal` or `diagnostic`
- `FREYA_PROMPT_FOR_MODE`: Set to `true` or `false` to enable/disable mode prompt
- `REOLINK_CAM_USER`: Camera username
- `REOLINK_CAM_PASS`: Camera password

### Configuration Files
The main configuration file (`config/default.yaml`) includes:

- **App Settings**: Wake word, interaction mode, system prompt
- **Ollama**: Model selection and API host
- **Speech-to-Text**: Device selection, model settings
- **Text-to-Speech**: Voice selection, speed settings
- **Memory**: Short-term and long-term storage configuration
- **Wake Detector**: Sensitivity and activation settings
- **Vision**: Camera and facial recognition settings

## Development

### Running Tests
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_startup.py

# Run with coverage
pytest --cov=freya tests/
```

### Code Quality
```bash
# Lint with ruff
ruff check .

# Auto-fix issues
ruff check --fix .

# Type check with mypy
mypy .
```

### CI/CD
The project includes GitHub Actions workflows for:
- Linting (ruff)
- Type checking (mypy)
- Testing (pytest)
- Dependency auditing (pip-audit)

## Project Structure

```
freya_project/
├── freya/                  # Main package
│   ├── orchestrator.py    # Core coordination logic
│   ├── config.py          # Configuration management
│   ├── memory.py          # Persistent memory system
│   ├── ollama_client.py   # LLM integration
│   ├── stt.py             # Speech-to-text
│   ├── tts.py             # Text-to-speech
│   ├── wake.py            # Wake word detection
│   ├── facial_recognition.py  # Face recognition
│   ├── rtsp_stream.py     # Camera streaming
│   ├── onvif_client.py    # Camera control
│   └── tools/             # Assistant tools (web search, etc.)
├── tests/                 # Test suite
├── config/                # Configuration files
├── data/                  # Data directory (faces, memory DB)
├── main.py                # Entry point
├── requirements.txt       # Production dependencies
└── pyproject.toml         # Package configuration
```

## Troubleshooting

### Audio Issues
- Check available audio devices: `python -c "import sounddevice as sd; print(sd.query_devices())"`
- Update device IDs in your config file
- Ensure microphone permissions are granted

### Ollama Connection
- Verify Ollama is running: `ollama list`
- Check the host setting in your config (default: `http://localhost:11434`)
- Ensure the model is pulled: `ollama pull <model-name>`

### Camera Connection
- Verify camera IP and credentials
- Test RTSP URL in VLC or other media player
- Check camera's RTSP settings are enabled

### Facial Recognition
- Install dlib and CMake (required for face_recognition)
- Ensure photos have clear, front-facing faces
- One face per image works best

## Contributing

Contributions are welcome! Please read the contribution guidelines before submitting a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Ollama](https://ollama.ai) for local LLM inference
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) for speech recognition
- [Piper TTS](https://github.com/rhasspy/piper) for text-to-speech
- [OpenCV](https://opencv.org/) for computer vision
- [face_recognition](https://github.com/ageitgey/face_recognition) library

---

**Note**: Freya is in active development. Features and APIs may change. For the latest updates, see the [GitHub repository](https://github.com/MrPink1977/freya_project).
