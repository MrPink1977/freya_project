# Building a Professional AI Assistant: A Complete Guide

**The Step-by-Step Process for Creating Your Own Local AI Assistant**

> Based on lessons learned from the Freya project, this guide provides a professional methodology for building a voice-enabled AI assistant with memory, personality, tools, and vision capabilities.

---

## Table of Contents

1. [Project Planning & Architecture](#1-project-planning--architecture)
2. [Directory Structure](#2-directory-structure)
3. [Development Phases](#3-development-phases)
4. [Detailed Implementation Steps](#4-detailed-implementation-steps)
5. [Testing Strategy](#5-testing-strategy)
6. [Professional Development Practices](#6-professional-development-practices)
7. [Technology Stack Decisions](#7-technology-stack-decisions)
8. [Common Pitfalls & Solutions](#8-common-pitfalls--solutions)

---

## 1. Project Planning & Architecture

### Phase 0: Define Your Vision (Week 1)

**Step 1.1: Define Core Requirements**

Create a `PROJECT_REQUIREMENTS.md` document:

```markdown
## Core Features
- [ ] Voice interaction (STT/TTS)
- [ ] Text chat mode
- [ ] Long-term memory with semantic search
- [ ] Personality system
- [ ] Tool/function calling
- [ ] Wake word detection
- [ ] Computer vision
- [ ] Multi-modal capabilities

## Non-Functional Requirements
- [ ] Run 100% locally (privacy-first)
- [ ] GPU acceleration support
- [ ] Modular/extensible architecture
- [ ] Comprehensive testing (>80% coverage)
- [ ] Production-ready error handling
- [ ] CI/CD pipeline
```

**Step 1.2: Choose Your Architecture Pattern**

**Recommended: Event-Driven Agent Architecture**

Why?
- ✅ Loose coupling between components
- ✅ Easy to add/remove features
- ✅ Async by default (better performance)
- ✅ Easier to test in isolation
- ✅ Scales well

Create `docs/ARCHITECTURE.md`:

```markdown
# Architecture Decision Record

## Pattern: Event-Driven Agents with Clean Architecture

### Components:
1. **MessageBus** - Async pub/sub system
2. **Agents** - Independent workers (Dialog, Memory, Tools, etc.)
3. **Coordinator** - Wires agents together
4. **Domain Layer** - Pure business logic
5. **Infrastructure Layer** - External integrations

### Communication Flow:
User Input → Event → Agent Processing → Event → Response
```

**Step 1.3: Design Your Data Flow**

Create a diagram:

```
┌──────────────┐
│  User Input  │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│   MessageBus         │
│   (Event Router)     │
└──────────────────────┘
       │
       ├─────────────┬─────────────┬─────────────┐
       ▼             ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Dialog  │  │  Memory  │  │  Tools   │  │  Speech  │
│  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
       │             │             │             │
       └─────────────┴─────────────┴─────────────┘
                       │
                       ▼
                 ┌──────────┐
                 │ Response │
                 └──────────┘
```

---

## 2. Directory Structure

### Recommended Clean Architecture Structure

```
my-ai-assistant/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    # CI/CD pipeline
│       └── security.yml              # Security scanning
│
├── config/
│   ├── default.yaml                  # Default configuration
│   ├── development.yaml              # Dev overrides
│   └── production.yaml               # Prod overrides
│
├── docs/
│   ├── ARCHITECTURE.md               # Architecture decisions
│   ├── API.md                        # API documentation
│   ├── DEPLOYMENT.md                 # Deployment guide
│   └── CONTRIBUTING.md               # Contribution guide
│
├── scripts/
│   ├── setup.sh                      # Initial setup script
│   ├── download_models.sh            # Download AI models
│   └── run_tests.sh                  # Test runner
│
├── src/                              # Main source code
│   └── assistant/                    # Your project name
│       │
│       ├── domain/                   # 🔵 DOMAIN LAYER (Pure logic)
│       │   ├── __init__.py
│       │   ├── entities/             # Business entities
│       │   │   ├── __init__.py
│       │   │   ├── memory.py         # Memory entity
│       │   │   ├── message.py        # Message entity
│       │   │   └── conversation.py   # Conversation entity
│       │   │
│       │   ├── interfaces/           # Abstract interfaces
│       │   │   ├── __init__.py
│       │   │   ├── agent.py          # Agent interface
│       │   │   ├── llm_client.py     # LLM client interface
│       │   │   ├── memory_store.py   # Memory store interface
│       │   │   └── message_bus.py    # Message bus interface
│       │   │
│       │   └── exceptions/           # Custom exceptions
│       │       ├── __init__.py
│       │       ├── base.py           # Base exception
│       │       ├── agent_errors.py   # Agent-specific errors
│       │       └── memory_errors.py  # Memory-specific errors
│       │
│       ├── application/              # 🟢 APPLICATION LAYER (Use cases)
│       │   ├── __init__.py
│       │   ├── use_cases/            # Business workflows
│       │   │   ├── __init__.py
│       │   │   ├── process_query.py  # Main query processing
│       │   │   └── store_memory.py   # Memory storage workflow
│       │   │
│       │   └── dtos/                 # Data transfer objects
│       │       ├── __init__.py
│       │       └── conversation_dto.py
│       │
│       ├── infrastructure/           # 🟠 INFRASTRUCTURE LAYER (Implementations)
│       │   ├── __init__.py
│       │   │
│       │   ├── agents/               # Agent implementations
│       │   │   ├── __init__.py
│       │   │   ├── base_agent.py     # Base agent with lifecycle
│       │   │   ├── dialog_agent.py   # LLM conversation
│       │   │   ├── memory_agent.py   # Memory management
│       │   │   ├── tool_agent.py     # Tool execution
│       │   │   ├── speech_agent.py   # STT/TTS coordination
│       │   │   └── wake_agent.py     # Wake word detection
│       │   │
│       │   ├── llm/                  # LLM integrations
│       │   │   ├── __init__.py
│       │   │   ├── ollama_client.py  # Ollama integration
│       │   │   └── openai_client.py  # OpenAI integration (optional)
│       │   │
│       │   ├── memory/               # Memory implementations
│       │   │   ├── __init__.py
│       │   │   ├── chroma_store.py   # ChromaDB vector store
│       │   │   ├── sqlite_store.py   # SQLite fallback
│       │   │   └── embedding.py      # Embedding models
│       │   │
│       │   ├── speech/               # Speech processing
│       │   │   ├── __init__.py
│       │   │   ├── stt/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── whisper_stt.py
│       │   │   │   └── base_stt.py
│       │   │   │
│       │   │   └── tts/
│       │   │       ├── __init__.py
│       │   │       ├── piper_tts.py
│       │   │       ├── elevenlabs_tts.py
│       │   │       └── base_tts.py
│       │   │
│       │   ├── vision/               # Computer vision
│       │   │   ├── __init__.py
│       │   │   ├── face_recognition.py
│       │   │   └── camera.py
│       │   │
│       │   ├── tools/                # Tool implementations
│       │   │   ├── __init__.py
│       │   │   ├── base_tool.py      # Base tool class
│       │   │   ├── tool_manager.py   # Tool registry
│       │   │   ├── time_tools.py     # Time/date tools
│       │   │   ├── file_tools.py     # File operations
│       │   │   ├── web_tools.py      # Web search/scraping
│       │   │   └── system_tools.py   # System info
│       │   │
│       │   └── messaging/            # Event system
│       │       ├── __init__.py
│       │       ├── message_bus.py    # Async pub/sub
│       │       └── events.py         # Event definitions
│       │
│       ├── presentation/             # 🟣 PRESENTATION LAYER (UI)
│       │   ├── __init__.py
│       │   ├── cli/                  # Command-line interface
│       │   │   ├── __init__.py
│       │   │   ├── main.py           # CLI entry point
│       │   │   └── commands.py       # CLI commands
│       │   │
│       │   └── web/                  # Web interface (optional)
│       │       ├── __init__.py
│       │       └── api.py            # REST/WebSocket API
│       │
│       ├── shared/                   # 🔷 SHARED LAYER (Cross-cutting)
│       │   ├── __init__.py
│       │   ├── logging/              # Structured logging
│       │   │   ├── __init__.py
│       │   │   └── logger.py
│       │   │
│       │   ├── config/               # Configuration management
│       │   │   ├── __init__.py
│       │   │   └── settings.py       # Settings dataclasses
│       │   │
│       │   └── utils/                # Utilities
│       │       ├── __init__.py
│       │       ├── retry.py          # Retry logic
│       │       ├── rate_limiter.py   # Rate limiting
│       │       └── circuit_breaker.py
│       │
│       └── coordination/             # 🎯 COORDINATION (Orchestration)
│           ├── __init__.py
│           └── coordinator.py        # Agent coordinator
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   │
│   ├── unit/                         # Unit tests
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   │
│   ├── integration/                  # Integration tests
│   │   ├── test_conversation_flow.py
│   │   └── test_memory_integration.py
│   │
│   └── e2e/                          # End-to-end tests
│       └── test_full_conversation.py
│
├── data/                             # Runtime data (gitignored)
│   ├── memory/                       # Memory persistence
│   ├── models/                       # Downloaded models
│   └── logs/                         # Application logs
│
├── .env.example                      # Example environment variables
├── .gitignore                        # Git ignore rules
├── .pylintrc                         # Linting configuration
├── mypy.ini                          # Type checking config
├── pytest.ini                        # Pytest configuration
├── requirements.txt                  # Production dependencies
├── requirements-dev.txt              # Development dependencies
├── setup.py                          # Package setup
├── README.md                         # Project overview
└── main.py                           # Application entry point
```

---

## 3. Development Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Set up project structure and core infrastructure

- [ ] Initialize git repository
- [ ] Set up directory structure
- [ ] Configure linting (ruff, black)
- [ ] Configure type checking (mypy)
- [ ] Set up pytest with coverage
- [ ] Create CI/CD pipeline (GitHub Actions)
- [ ] Write README and initial docs

### Phase 2: Core Infrastructure (Weeks 3-4)

**Goal**: Build the event system and base agent framework

- [ ] Implement MessageBus (async pub/sub)
- [ ] Create BaseAgent class with lifecycle
- [ ] Implement configuration system (YAML + env vars)
- [ ] Set up structured logging
- [ ] Create custom exception hierarchy
- [ ] Write unit tests for all core components

### Phase 3: LLM Integration (Weeks 5-6)

**Goal**: Get basic conversation working

- [ ] Implement Ollama client with retry logic
- [ ] Create DialogAgent with streaming
- [ ] Add short-term context management
- [ ] Implement basic personality system
- [ ] Create text-mode CLI interface
- [ ] Write integration tests

### Phase 4: Memory System (Weeks 7-8)

**Goal**: Add persistent memory with semantic search

- [ ] Integrate ChromaDB
- [ ] Implement embedding generation (nomic-embed-text)
- [ ] Create MemoryAgent
- [ ] Add automatic memory storage triggers
- [ ] Implement memory retrieval in conversations
- [ ] Test memory reliability and corruption recovery

### Phase 5: Tool System (Weeks 9-10)

**Goal**: Enable function calling capabilities

- [ ] Create base tool framework
- [ ] Implement ToolManager registry
- [ ] Create ToolExecutorAgent
- [ ] Implement 5-10 basic tools:
  - Time/date tools
  - Calculator
  - File operations
  - Web search
  - Web scraping
- [ ] Add tool security (whitelisting, validation)
- [ ] Write tool tests

### Phase 6: Speech Pipeline (Weeks 11-13)

**Goal**: Add voice interaction

- [ ] Integrate Faster Whisper (STT)
- [ ] Integrate Piper TTS (local)
- [ ] Optional: Integrate ElevenLabs (cloud)
- [ ] Create SpeechAgent for coordination
- [ ] Add microphone/speaker management
- [ ] Implement audio preprocessing (silence detection)
- [ ] Test STT/TTS pipeline

### Phase 7: Wake Word Detection (Week 14)

**Goal**: Enable always-listening mode

- [ ] Implement WakeWordAgent
- [ ] Use Whisper tiny for detection
- [ ] Add configurable sensitivity
- [ ] Implement session window logic
- [ ] Test background listening
- [ ] Optimize CPU/GPU usage

### Phase 8: Computer Vision (Weeks 15-16)

**Goal**: Add visual capabilities

- [ ] Integrate face_recognition library
- [ ] Create VisionAgent
- [ ] Add RTSP camera support
- [ ] Implement facial recognition
- [ ] Optional: Add object detection (YOLO)
- [ ] Test vision pipeline

### Phase 9: Coordination & Polish (Weeks 17-18)

**Goal**: Wire everything together

- [ ] Create OrchestrationCoordinator
- [ ] Wire all agents via MessageBus
- [ ] Add health monitoring
- [ ] Implement backpressure handling
- [ ] Add circuit breakers
- [ ] Create startup system checks
- [ ] End-to-end testing

### Phase 10: Production Readiness (Weeks 19-20)

**Goal**: Make it production-grade

- [ ] Comprehensive error handling
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation completion
- [ ] Deployment guide
- [ ] User manual
- [ ] Performance benchmarks

---

## 4. Detailed Implementation Steps

### Step 1: Initialize Project (Day 1)

```bash
# Create project directory
mkdir my-ai-assistant
cd my-ai-assistant

# Initialize git
git init
git branch -M main

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Create basic structure
mkdir -p src/assistant/{domain,application,infrastructure,presentation,shared,coordination}
mkdir -p tests/{unit,integration,e2e}
mkdir -p config docs scripts data

# Initialize Python package
touch src/assistant/__init__.py
touch tests/__init__.py

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
dist/
build/

# Data & Models
data/
*.db
*.pt
*.onnx
*.bin

# IDE
.vscode/
.idea/
*.swp

# Environment
.env
.env.local

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db
EOF

# Create README
cat > README.md << 'EOF'
# My AI Assistant

A local, voice-enabled AI assistant with memory, personality, and tool capabilities.

## Features
- 🎤 Voice interaction (STT/TTS)
- 🧠 Long-term memory with semantic search
- 🛠️ Function calling and tool usage
- 👤 Adaptive personality system
- 👁️ Computer vision capabilities

## Getting Started
See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
EOF
```

### Step 2: Set Up Development Tools (Day 1-2)

```bash
# Create requirements.txt
cat > requirements.txt << 'EOF'
# Core
requests>=2.31.0
PyYAML>=6.0
python-dotenv>=1.0.0
pydantic>=2.0.0

# LLM & Embeddings
chromadb>=0.4.0
sentence-transformers>=2.2.0
ollama>=0.1.0

# Speech
faster-whisper>=0.9.0
piper-tts>=1.2.0
sounddevice>=0.4.6
soundfile>=0.12.1

# Tools & Web
beautifulsoup4>=4.12.0
lxml>=4.9.0
duckduckgo-search>=3.9.0

# Vision
opencv-python>=4.8.0
face-recognition>=1.3.0
Pillow>=10.0.0

# Utilities
tenacity>=8.2.0
psutil>=5.9.0
colorama>=0.4.6
EOF

# Create requirements-dev.txt
cat > requirements-dev.txt << 'EOF'
-r requirements.txt

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0

# Linting & Formatting
ruff>=0.1.0
black>=23.0.0
mypy>=1.5.0

# Security
pip-audit>=2.6.0
bandit>=1.7.5

# Documentation
mkdocs>=1.5.0
mkdocs-material>=9.0.0
EOF

# Install dependencies
pip install -r requirements-dev.txt

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-ai-assistant"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=src/assistant --cov-report=html --cov-report=term"
EOF
```

### Step 3: Create Core Configuration System (Day 2-3)

```python
# src/assistant/shared/config/settings.py
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
import yaml
import os


@dataclass(frozen=True)
class OllamaConfig:
    host: str
    model: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class MemoryConfig:
    enabled: bool
    persist_directory: str
    embedding_model: str
    max_history: int


@dataclass(frozen=True)
class Settings:
    ollama: OllamaConfig
    memory: MemoryConfig
    # Add more config sections as needed


def load_settings(config_path: Path | None = None) -> Settings:
    """Load configuration from YAML file with environment variable overrides."""
    if config_path is None:
        config_path = Path("config/default.yaml")

    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    # Load with environment variable overrides
    ollama_config = OllamaConfig(
        host=os.getenv("OLLAMA_HOST") or config_data["ollama"]["host"],
        model=os.getenv("OLLAMA_MODEL") or config_data["ollama"]["model"],
        temperature=float(config_data["ollama"]["temperature"]),
        max_tokens=int(config_data["ollama"]["max_tokens"]),
    )

    memory_config = MemoryConfig(
        enabled=bool(config_data["memory"]["enabled"]),
        persist_directory=os.getenv("MEMORY_DIR") or config_data["memory"]["persist_directory"],
        embedding_model=config_data["memory"]["embedding_model"],
        max_history=int(config_data["memory"]["max_history"]),
    )

    return Settings(ollama=ollama_config, memory=memory_config)
```

```yaml
# config/default.yaml
ollama:
  host: "http://localhost:11434"
  model: "llama3.2:3b"
  temperature: 0.7
  max_tokens: 500

memory:
  enabled: true
  persist_directory: "data/memory"
  embedding_model: "nomic-embed-text:latest"
  max_history: 10
```

### Step 4: Implement MessageBus (Day 3-4)

```python
# src/assistant/infrastructure/messaging/message_bus.py
import asyncio
from collections import defaultdict
from typing import Any, Callable, Dict, List
import logging

logger = logging.getLogger(__name__)


class MessageBus:
    """Async pub/sub message bus for agent communication."""

    def __init__(self, max_queue_size: int = 1000):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._max_queue_size = max_queue_size
        self._message_count = 0

    def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe to a topic with a handler function."""
        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        """Unsubscribe a handler from a topic."""
        if handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)
            logger.debug(f"Unsubscribed from topic: {topic}")

    async def publish(self, topic: str, data: Any) -> None:
        """Publish a message to all subscribers of a topic."""
        self._message_count += 1

        if topic not in self._subscribers:
            logger.debug(f"No subscribers for topic: {topic}")
            return

        logger.debug(f"Publishing to topic: {topic} ({len(self._subscribers[topic])} subscribers)")

        # Call all handlers concurrently
        tasks = []
        for handler in self._subscribers[topic]:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(data))
            else:
                # Wrap sync functions
                tasks.append(asyncio.to_thread(handler, data))

        await asyncio.gather(*tasks, return_exceptions=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            "total_messages": self._message_count,
            "topics": list(self._subscribers.keys()),
            "subscriber_counts": {
                topic: len(handlers)
                for topic, handlers in self._subscribers.items()
            }
        }
```

### Step 5: Create BaseAgent (Day 4-5)

```python
# src/assistant/infrastructure/agents/base_agent.py
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class BaseAgent(ABC):
    """Base class for all agents with lifecycle management."""

    def __init__(self, name: str):
        self.name = name
        self.state = AgentState.CREATED
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent. Override in subclasses."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up resources. Override in subclasses."""
        pass

    async def start(self) -> None:
        """Start the agent."""
        logger.info(f"Starting agent: {self.name}")
        self.state = AgentState.INITIALIZING

        try:
            await self.initialize()
            self.state = AgentState.READY
            logger.info(f"Agent {self.name} is ready")
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Failed to initialize agent {self.name}: {e}")
            raise

    async def stop(self) -> None:
        """Stop the agent."""
        logger.info(f"Stopping agent: {self.name}")
        self._stop_event.set()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self.shutdown()
        self.state = AgentState.STOPPED
        logger.info(f"Agent {self.name} stopped")

    def is_running(self) -> bool:
        """Check if agent is running."""
        return self.state in (AgentState.READY, AgentState.BUSY)
```

### Step 6: First Test - MessageBus (Day 5)

```python
# tests/unit/infrastructure/test_message_bus.py
import pytest
import asyncio
from src.assistant.infrastructure.messaging.message_bus import MessageBus


@pytest.mark.asyncio
async def test_publish_subscribe():
    """Test basic pub/sub functionality."""
    bus = MessageBus()
    received_messages = []

    async def handler(data):
        received_messages.append(data)

    bus.subscribe("test.topic", handler)
    await bus.publish("test.topic", {"message": "Hello"})

    # Wait a bit for async processing
    await asyncio.sleep(0.1)

    assert len(received_messages) == 1
    assert received_messages[0]["message"] == "Hello"


@pytest.mark.asyncio
async def test_multiple_subscribers():
    """Test multiple subscribers to same topic."""
    bus = MessageBus()
    received_a = []
    received_b = []

    async def handler_a(data):
        received_a.append(data)

    async def handler_b(data):
        received_b.append(data)

    bus.subscribe("test", handler_a)
    bus.subscribe("test", handler_b)

    await bus.publish("test", "message")
    await asyncio.sleep(0.1)

    assert len(received_a) == 1
    assert len(received_b) == 1


@pytest.mark.asyncio
async def test_unsubscribe():
    """Test unsubscribe functionality."""
    bus = MessageBus()
    received = []

    async def handler(data):
        received.append(data)

    bus.subscribe("test", handler)
    await bus.publish("test", "msg1")

    bus.unsubscribe("test", handler)
    await bus.publish("test", "msg2")

    await asyncio.sleep(0.1)

    assert len(received) == 1  # Only first message
```

Run tests:
```bash
pytest tests/unit/infrastructure/test_message_bus.py -v
```

---

## 5. Testing Strategy

### Testing Pyramid

```
           ╱╲
          ╱  ╲
         ╱ E2E ╲          10% - Full system tests
        ╱──────╲
       ╱        ╲
      ╱Integration╲       30% - Agent integration tests
     ╱────────────╲
    ╱              ╲
   ╱  Unit Tests    ╲     60% - Component tests
  ╱──────────────────╲
```

### Test Organization

```python
# tests/conftest.py
import pytest
import asyncio
from src.assistant.infrastructure.messaging.message_bus import MessageBus
from src.assistant.shared.config.settings import Settings, OllamaConfig, MemoryConfig


@pytest.fixture
def message_bus():
    """Provide a fresh message bus for each test."""
    return MessageBus()


@pytest.fixture
def test_settings():
    """Provide test configuration."""
    return Settings(
        ollama=OllamaConfig(
            host="http://localhost:11434",
            model="llama3.2:3b",
            temperature=0.7,
            max_tokens=100,
        ),
        memory=MemoryConfig(
            enabled=True,
            persist_directory="data/test_memory",
            embedding_model="nomic-embed-text",
            max_history=5,
        ),
    )


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

### Test Coverage Goals

- **Unit Tests**: 80%+ coverage
- **Integration Tests**: All agent interactions
- **E2E Tests**: Main user workflows
- **Performance Tests**: Response time benchmarks

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt

    - name: Lint with ruff
      run: ruff check src/

    - name: Type check with mypy
      run: mypy src/

    - name: Test with pytest
      run: pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

    - name: Security audit
      run: pip-audit
```

---

## 6. Professional Development Practices

### 1. Version Control Strategy

**Git Flow**:
- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `release/*` - Release preparation

**Commit Messages**:
```
type(scope): subject

body

footer
```

Example:
```
feat(dialog): add streaming LLM responses

- Implement async streaming from Ollama
- Add chunked response handling
- Update DialogAgent to support streaming

Closes #123
```

### 2. Code Quality Standards

**Style Guide**:
- Follow PEP 8
- Use type hints everywhere
- Max line length: 100 characters
- Docstrings for all public functions

**Example**:
```python
from typing import List, Optional


def process_query(
    query: str,
    context: List[str],
    temperature: float = 0.7
) -> Optional[str]:
    """
    Process user query with context.

    Args:
        query: User's question or command
        context: List of previous messages
        temperature: LLM sampling temperature (0-1)

    Returns:
        Generated response or None if failed

    Raises:
        ValueError: If temperature is out of range
    """
    if not 0 <= temperature <= 1:
        raise ValueError("Temperature must be between 0 and 1")

    # Implementation
    pass
```

### 3. Logging Standards

```python
# src/assistant/shared/logging/logger.py
import logging
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> None:
    """Configure structured logging."""

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers,
    )
```

Usage:
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing user query", extra={
    "user_id": "123",
    "query_length": len(query)
})
```

### 4. Error Handling

**Custom Exception Hierarchy**:
```python
# src/assistant/domain/exceptions/base.py
class AssistantError(Exception):
    """Base exception for all assistant errors."""
    pass


class AgentError(AssistantError):
    """Agent-specific errors."""
    pass


class LLMError(AssistantError):
    """LLM communication errors."""
    pass


class MemoryError(AssistantError):
    """Memory system errors."""
    pass
```

**Retry Logic**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_llm(prompt: str) -> str:
    """Call LLM with automatic retry on failure."""
    # Implementation
    pass
```

### 5. Documentation Standards

**README.md Structure**:
```markdown
# Project Name

Brief description

## Features
- List of features

## Installation
Step-by-step installation

## Quick Start
Minimal example to get running

## Configuration
How to configure

## Development
How to contribute

## License
```

**API Documentation**:
- Use docstrings for all public APIs
- Generate docs with mkdocs
- Include code examples

---

## 7. Technology Stack Decisions

### LLM Provider

**Ollama (Recommended)**:
- ✅ Runs locally (privacy)
- ✅ Free and open source
- ✅ Easy model switching
- ✅ Good performance
- ❌ Requires local resources

**Alternatives**:
- OpenAI API (cloud, costs money)
- Anthropic Claude (cloud, costs money)
- LM Studio (local, GUI focused)

### Memory/Vector Database

**ChromaDB (Recommended)**:
- ✅ Easy to use
- ✅ Good performance
- ✅ Open source
- ✅ Active development

**Alternatives**:
- Qdrant (more features, heavier)
- Milvus (production-scale)
- Weaviate (GraphQL interface)

### Speech-to-Text

**Faster Whisper (Recommended)**:
- ✅ Excellent accuracy
- ✅ Local processing
- ✅ GPU acceleration
- ✅ Multiple model sizes

**Alternatives**:
- Vosk (lighter, less accurate)
- Coqui STT (discontinued)
- Cloud APIs (Google, Azure, AWS)

### Text-to-Speech

**Piper (Recommended for local)**:
- ✅ Fast
- ✅ Good quality
- ✅ Many voices
- ✅ Low resource usage

**ElevenLabs (Recommended for quality)**:
- ✅ Best quality
- ✅ Voice cloning
- ❌ Costs money
- ❌ Cloud-based

---

## 8. Common Pitfalls & Solutions

### Pitfall 1: Tight Coupling

**Problem**: Agents directly calling each other
```python
# ❌ Bad
class DialogAgent:
    def __init__(self, memory_agent):
        self.memory = memory_agent

    async def process(self, query):
        memories = self.memory.recall(query)  # Tight coupling!
```

**Solution**: Use MessageBus
```python
# ✅ Good
class DialogAgent:
    def __init__(self, message_bus):
        self.bus = message_bus
        self.bus.subscribe("memory.results", self.handle_memories)

    async def process(self, query):
        await self.bus.publish("memory.query", query)
```

### Pitfall 2: Blocking Async Code

**Problem**: Blocking calls in async functions
```python
# ❌ Bad
async def process_audio(file_path):
    audio_data = file_path.read_bytes()  # Blocks event loop!
```

**Solution**: Use asyncio.to_thread
```python
# ✅ Good
async def process_audio(file_path):
    audio_data = await asyncio.to_thread(file_path.read_bytes)
```

### Pitfall 3: Poor Error Handling

**Problem**: Silent failures
```python
# ❌ Bad
try:
    result = await llm.generate(prompt)
except:
    pass  # Swallows all errors!
```

**Solution**: Specific exceptions and logging
```python
# ✅ Good
try:
    result = await llm.generate(prompt)
except ConnectionError as e:
    logger.error(f"LLM connection failed: {e}")
    raise LLMError("Failed to connect to LLM") from e
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### Pitfall 4: No Testing

**Problem**: Writing code without tests
```python
# Write feature → Deploy → Hope it works
```

**Solution**: Test-Driven Development
```python
# 1. Write test
def test_calculator():
    calc = Calculator()
    assert calc.add(2, 2) == 4

# 2. Write code
class Calculator:
    def add(self, a, b):
        return a + b

# 3. Verify test passes
# 4. Refactor
```

### Pitfall 5: Overengineering

**Problem**: Building for every possible future scenario

**Solution**: YAGNI (You Aren't Gonna Need It)
- Build only what you need now
- Add features when actually needed
- Keep it simple

---

## Quick Start Checklist

### Week 1: Setup
- [ ] Initialize repository
- [ ] Set up directory structure
- [ ] Configure development tools (linting, testing)
- [ ] Create CI/CD pipeline
- [ ] Write initial documentation

### Week 2-3: Core Infrastructure
- [ ] Implement MessageBus
- [ ] Create BaseAgent
- [ ] Set up configuration system
- [ ] Add structured logging
- [ ] Write unit tests (aim for 80%+ coverage)

### Week 4-5: LLM Integration
- [ ] Implement Ollama client
- [ ] Create DialogAgent
- [ ] Add context management
- [ ] Build text-mode CLI
- [ ] Integration tests

### Week 6-7: Memory System
- [ ] Integrate ChromaDB
- [ ] Create MemoryAgent
- [ ] Implement embedding generation
- [ ] Add automatic storage
- [ ] Memory reliability tests

### Week 8-9: Tools
- [ ] Build tool framework
- [ ] Create 5-10 basic tools
- [ ] Add security measures
- [ ] Tool execution tests

### Week 10-12: Speech
- [ ] Integrate STT (Whisper)
- [ ] Integrate TTS (Piper)
- [ ] Create SpeechAgent
- [ ] Audio pipeline tests

### Week 13-14: Wake Word
- [ ] Implement wake detection
- [ ] Background listening
- [ ] Optimize performance

### Week 15-16: Vision
- [ ] Add facial recognition
- [ ] Camera integration
- [ ] Vision tests

### Week 17-18: Polish
- [ ] Wire all agents
- [ ] Add health monitoring
- [ ] End-to-end tests
- [ ] Performance optimization

### Week 19-20: Production
- [ ] Security audit
- [ ] Documentation
- [ ] Deployment guide
- [ ] Final testing

---

## Resources & Learning

### Essential Reading
- Clean Architecture by Robert C. Martin
- Designing Data-Intensive Applications by Martin Kleppmann
- Python Concurrency with Asyncio by Matthew Fowler

### Tools & Libraries
- **Ollama**: https://ollama.com/
- **ChromaDB**: https://www.trychroma.com/
- **Faster Whisper**: https://github.com/guillaumekln/faster-whisper
- **Piper TTS**: https://github.com/rhasspy/piper

### Communities
- r/LocalLLaMA (Reddit)
- Ollama Discord
- LangChain Discord

---

## Final Thoughts

Building a professional AI assistant is a marathon, not a sprint. Focus on:

1. **Solid Foundations** - Clean architecture pays off
2. **Testing** - Write tests from day one
3. **Iteration** - Build incrementally
4. **Documentation** - Future you will thank you
5. **Community** - Share and learn from others

Good luck building your AI assistant! 🚀
