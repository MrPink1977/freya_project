# Freya - Voice-Enabled AI Assistant

Freya is a sophisticated voice-enabled AI assistant with computer vision capabilities, built on a modern **agent-based architecture**. It combines speech recognition, natural language processing via Ollama, ChromaDB vector memory, and camera integration to create an interactive, context-aware JARVIS-style assistant.

## Architecture

Freya uses an **event-driven microservices architecture** with specialized agents communicating through a central MessageBus. This modular design enables:
- **Scalability**: Add new capabilities without touching existing code
- **Maintainability**: Each agent handles one concern (memory, dialog, tools, etc.)
- **Testability**: Agents can be tested independently
- **Performance**: Async/await throughout for responsive interactions

### Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                    MessageBus (Pub/Sub)                     │
│             Event-driven communication backbone              │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  WakeWordAgent   │  │   DialogAgent    │  │  MemoryAgent     │
│                  │  │                  │  │                  │
│ • Background     │  │ • LLM streaming  │  │ • ChromaDB       │
│   listening      │  │ • Smart model    │  │ • Vector search  │
│ • Session        │  │   escalation     │  │ • Fact extraction│
│   windows        │  │ • Context mgmt   │  │ • Semantic query │
└──────────────────┘  └──────────────────┘  └──────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ToolExecutorAgent │  │  Coordinator     │  │  Future Agents   │
│                  │  │                  │  │                  │
│ • Pattern-based  │  │ • Agent lifecycle│  │ • VisionAgent    │
│ • 9 tool types   │  │ • Event routing  │  │ • SpeechAgent    │
│ • Time, calc,    │  │ • Mode switching │  │ • IoTAgent       │
│   files, web     │  │ • TTS/STT bridge │  │ • AutomationAgent│
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Message Flow Example

```
User: "Hey Freya, what time is it?"
  ↓
┌─────────────────────────────────────────────────────────┐
│ WakeWordAgent: Detects wake word                       │
│   Publishes: wake.detected                             │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ Coordinator: Receives wake.detected                     │
│   1. Query MemoryAgent for relevant context            │
│   2. Inject memories into DialogAgent                  │
│   3. Publish dialog.request                            │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ DialogAgent: Generates LLM response                     │
│   1. Start with llama3.2:3b (fast)                     │
│   2. Stream chunks → dialog.chunk                       │
│   3. Publish dialog.complete                           │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ Coordinator: Routes dialog.chunk to TTS                 │
│   User hears: "The current time is 3:42 PM"            │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ MemoryAgent: Stores conversation                       │
│   Publishes: memory.stored                             │
└─────────────────────────────────────────────────────────┘
```

## Features

### Core Voice Assistant
- **Speech-to-Text**: Dual-Whisper architecture (tiny model for wake word, base model for full transcription)
- **Text-to-Speech**: Multiple engines (Piper local, ElevenLabs API, ElevenLabs MCP)
- **Wake Word Detection**: Background always-listening with session windows
- **Smart Memory**: ChromaDB vector storage with semantic search (O(log n) HNSW indexing)
- **Context Management**: Automatic transfer to long-term memory at 75% capacity
- **Model Escalation**: Starts with fast llama3.2:3b, escalates to dolphin-mixtral on confusion
- **MCP Integration**: Model Context Protocol support for standardized tool ecosystem

### Vision Capabilities
- **Facial Recognition**: Identify known individuals using face_recognition library
- **RTSP Camera Integration**: Connect to IP cameras for video streaming
- **ONVIF Support**: Control cameras that support ONVIF protocol
- **Multi-Channel Audio**: Coordinate audio from multiple sources (mic + cameras)

### AI Integration
- **Ollama Backend**: Flexible LLM integration with multiple models
- **Multi-Model Strategy**: llama3.2:3b (fast), dolphin-mixtral:8x7b (reasoning), deepseek-coder-v2:16b-lite (code)
- **Streaming Responses**: Real-time text-to-speech streaming during generation
- **Tool Integration**: 9 built-in tools (time, date, calculator, files, system, web search, performance)
- **MCP Servers**: Extensible Model Context Protocol integration for ecosystem-wide tools

### Interaction Modes
- **Voice Mode**: Hands-free conversation with wake word detection
- **Text Mode**: Terminal-based chat interface with colored output
- **Natural Exit Commands**: Say "be quiet", "zip it", "shut up" to exit gracefully

### Emergency Controls
- **Ctrl+M**: Mute/stop current speech immediately
- **Escape**: Emergency stop for when Freya won't stop talking
- **Natural Language**: Say commands like "be quiet" or "shut up"

### Visual Enhancements
- **Colored Conversation**: User messages in cyan, Freya in magenta
- **Startup System Checks**: Visual checkmarks for each component
- **Formatted Output**: Box-style formatting for clear conversation flow

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
# Create virtual environment
python -m venv freya_env
source freya_env/bin/activate  # On Windows: freya_env\Scripts\activate

# Install dependencies (recommended - installs package in editable mode)
pip install -e .

# Or install with dev tools for testing and linting
pip install -e ".[dev]"

# For facial recognition (optional)
pip install -e ".[face-recognition]"
```

### 3. Configure Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set your API keys
# ELEVENLABS_API_KEY=sk_your_api_key_here  # For ElevenLabs TTS (optional)
# ELEVENLABS_VOICE_ID=your_voice_id_here   # Custom voice ID (optional)
```

### 3.5. Install MCP Servers (Optional)
For enhanced capabilities using Model Context Protocol:

```bash
# Install ElevenLabs MCP for premium TTS
pip install elevenlabs-mcp==0.9.0

# More MCP servers coming soon (web search, memory, etc.)
```

See `docs/ELEVENLABS_MCP_INTEGRATION.md` for complete MCP setup guide.

### 4. Install Ollama
Download and install Ollama from [ollama.ai](https://ollama.ai)

```bash
# Pull recommended models
ollama pull llama3.2:3b              # Fast model (2GB VRAM)
ollama pull dolphin-mixtral:8x7b     # Reasoning model (26GB VRAM)
ollama pull deepseek-coder-v2:16b-lite  # Code model (10GB VRAM)

# Minimum: just the fast model
ollama pull llama3.2:3b
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
- **Memory**: ChromaDB storage path and retrieval settings
- **Vision**: Camera credentials and facial recognition setup
- **Agents**: Enable/disable specific agents, configure models

## Usage

### Quick Start
```bash
# Run with system checks and startup menu
python main.py

# Run system check only (verify setup)
python main.py --check

# Run in text mode (no voice)
python main.py --mode text

# Use specific config file
python main.py --config config/my_config.yaml
```

### Startup Display
When you launch Freya, you'll see:
```
======================================================================
  FREYA - Voice AI Assistant
  Agent Architecture | Multi-Channel Audio | 9 Tools
======================================================================

Configuration:
  • Mode: VOICE
  • LLM Model: llama3.2:3b
  • TTS Engine: elevenlabs
  • Wake Word: 'Hey, Freya'

Controls:
  • Ctrl+M - Mute/stop speech immediately
  • Escape - Emergency stop
  • Natural exit - Say 'be quiet', 'zip it', 'shut up'

System Checks:
  ✓ Ollama Connection............................ OK
  ✓ Whisper STT Model............................ OK
  ✓ Microphone Access............................ OK
  ✓ TTS Engine................................... OK
  ✓ Wake Word Detector........................... OK
  ✓ Memory Store................................. OK

✓ All systems operational!
```

### Basic Usage
```bash
# Run with agent architecture (default)
python main.py

# Run with custom config
python main.py --config config/my_config.yaml --use-agents

# Run in text mode (no voice)
python main.py --mode text --use-agents

# Run with legacy orchestrator (deprecated)
python main.py

# Diagnostic mode (detailed logs)
python main.py --startup-mode diagnostic --use-agents
```

### Agent Architecture vs Legacy

**New Agent Architecture** (Recommended):
```bash
python main.py --use-agents
```
- Event-driven, modular design
- Smart model escalation (llama3.2 → dolphin-mixtral)
- ChromaDB vector memory with semantic search
- 75% context auto-transfer to long-term memory
- Parallel agent execution
- Extensible via new agents

**Legacy Orchestrator** (Deprecated):
```bash
python main.py
```
- Monolithic design
- Single model, no escalation
- SQLite memory (slower)
- Fixed context window
- Will be removed in future release

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
├── freya/                      # Main package
│   ├── agents/                 # Intelligent agents
│   │   ├── base_agent.py       # Abstract agent class
│   │   ├── dialog_agent.py     # LLM conversation (streaming, escalation)
│   │   ├── memory_agent.py     # ChromaDB memory coordination
│   │   ├── tool_executor_agent.py  # Tool detection/execution
│   │   └── wake_word_agent.py  # Background wake detection
│   │
│   ├── core/                   # Foundation infrastructure
│   │   └── message_bus.py      # Event-driven pub/sub system
│   │
│   ├── coordination/           # Agent orchestration
│   │   └── orchestration_coordinator.py  # Lightweight coordinator
│   │
│   ├── tools/                  # Tool implementations
│   │   ├── calculator.py       # Math operations
│   │   ├── datetime_tools.py   # Time/date utilities
│   │   ├── file_tools.py       # File operations
│   │   ├── system_tools.py     # System information
│   │   ├── web_search.py       # DuckDuckGo search
│   │   └── web_scraper.py      # Web content extraction
│   │
│   ├── orchestrator.py         # Legacy orchestrator (deprecated)
│   ├── config.py               # Configuration management
│   ├── memory.py               # ChromaDB vector store
│   ├── context.py              # Conversation context
│   ├── ollama_client.py        # LLM integration
│   ├── stt.py                  # Speech-to-text
│   ├── tts.py                  # Text-to-speech (Piper)
│   ├── tts_elevenlabs.py       # ElevenLabs TTS
│   ├── wake.py                 # Wake word detection (Whisper)
│   ├── wake_word_matcher.py    # Fuzzy wake word matching
│   ├── facial_recognition.py   # Face recognition
│   ├── rtsp_stream.py          # Camera streaming
│   └── onvif_client.py         # Camera control
│
├── tests/                      # Test suite
│   ├── test_agent_foundation.py
│   ├── test_tool_executor_agent.py
│   ├── test_chroma_memory.py
│   ├── test_memory_agent.py
│   ├── test_wake_word_agent.py
│   ├── test_dialog_agent.py
│   └── test_orchestration_coordinator.py
│
├── config/                     # Configuration files
│   └── default.yaml            # Default configuration
├── data/                       # Data directory
│   ├── faces/                  # Known faces for recognition
│   └── chroma_db/              # ChromaDB vector storage
├── main.py                     # Entry point
├── pyproject.toml              # Package configuration & dependencies
├── .env.example                # Environment variables template
└── .env                        # Local environment variables (not in git)
```

## Future Enhancements

### Planned Agents (Roadmap)

**Phase 2: Sensory Layer**
- **SpeechAgent**: Unified STT/TTS agent replacing legacy components
- **VisionAgent**: Camera processing, facial recognition, object detection (YOLO integration)

**Phase 3: Intelligence Layer**
- **ContextAnalyzerAgent**: Intent detection, entity extraction, emotion analysis
- **LearningAgent**: Pattern learning, user preference adaptation, behavior prediction

**Phase 4: Control Layer**
- **IoTAgent**: Smart home integration (Home Assistant, Philips Hue, smart plugs)
- **AutomationAgent**: Scheduled tasks, routines, reminders, time-based actions

**Phase 5: Advanced Capabilities**
- **ResearchAgent**: Multi-step web research, fact-checking, source synthesis
- **CodeAgent**: Code generation, debugging, sandbox execution (uses deepseek-coder)
- **PersonalityAgent**: Emotional intelligence, mood-based responses, adaptive personality
- **MultimodalAgent**: Vision + voice fusion, gesture recognition, spatial awareness

### Technical Improvements

**Performance**
- GPU acceleration for vision tasks (CUDA/ROCm support)
- Model quantization for lower VRAM usage
- Parallel agent execution for faster responses
- Edge deployment on Jetson/RPi for local-first privacy

**Memory System**
- Episodic memory: Event-based timeline ("user laughed at 3pm")
- Working memory: Redis-like short-term cache
- Memory consolidation: Automatic summarization and archival
- Multi-user memory: Per-user context isolation

**Multi-Modal Integration**
- Vision-language models (LLaVA, BakLLaVA)
- Screen reading and UI automation
- Gesture control via camera
- Emotion detection from voice tone

**Scalability**
- Distributed agents across multiple machines
- Agent hot-reloading for zero-downtime updates
- Message queue persistence (Redis, RabbitMQ)
- Kubernetes deployment for cloud scaling

**Developer Experience**
- Web UI for agent monitoring
- Real-time agent performance metrics
- Visual agent graph editor
- Plugin system for custom agents

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
- [ChromaDB](https://www.trychroma.com/) for vector database
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) for speech recognition
- [Piper TTS](https://github.com/rhasspy/piper) for text-to-speech
- [OpenCV](https://opencv.org/) for computer vision
- [face_recognition](https://github.com/ageitgey/face_recognition) library

## Development Status

**Current Version**: Agent Architecture (v2.0)
- ✅ MessageBus event system
- ✅ ToolExecutorAgent (9 tools)
- ✅ MemoryAgent (ChromaDB)
- ✅ WakeWordAgent (background detection)
- ✅ DialogAgent (streaming LLM with escalation)
- ✅ OrchestrationCoordinator
- ⬜ SpeechAgent (planned)
- ⬜ VisionAgent (planned)
- ⬜ ContextAnalyzerAgent (planned)

**Branch**: `feature/agent-architecture` (merging to `main` soon)

---

**Note**: Freya is in active development. The agent architecture is production-ready but undergoing final testing before merge. For the latest updates, see the [GitHub repository](https://github.com/MrPink1977/freya_project).
