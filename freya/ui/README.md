# Freya TUI - Terminal User Interface

Modern terminal-based UI for Freya AI Assistant built with [Textual](https://textual.textualize.io/).

## Quick Start

```bash
# Install dependencies (already done if you ran pip install)
pip install textual rich

# Launch TUI
python main_ui.py
```

## Features

### ✅ System Checks (F1) - **COMPLETE**
- Real-time health monitoring for all components
- Visual status indicators (✓/⚠/✗)
- Detailed error messages with fix suggestions
- Performance timing for each check
- Components checked:
  - Python environment (version 3.11+)
  - Ollama connection and models
  - Whisper STT availability
  - Microphone access
  - Speaker/audio output
  - TTS engine (Piper/ElevenLabs)
  - ChromaDB memory store

### 🚧 Coming Soon

#### Configuration Screen (F2)
- Tree-based navigation for settings categories
- Live config editing without touching YAML
- Model selection dropdown
- Wake word sensitivity sliders
- Apply/Reset/Save & Restart actions

#### Chat Interface (F3)
- Live chat with Freya in the terminal
- Colored message bubbles (user vs assistant)
- Streaming responses
- Tool execution indicators
- Token count and response time display
- MessageBus integration for real-time updates

#### Log Viewer (F4)
- Real-time log streaming
- Filter by level (DEBUG/INFO/WARNING/ERROR)
- Filter by agent (Dialog/Memory/Wake/Tool/Speech)
- Search functionality
- Export logs to file
- Auto-scroll toggle

#### Test Runner (F5)
- Run pytest integration tests from UI
- Collapsible test suites
- Real-time progress indicators
- Pass/fail/skip status
- Detailed failure information
- Rerun failed tests
- Export test reports

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **F1** | System Checks |
| **F2** | Configuration |
| **F3** | Chat Interface |
| **F4** | Log Viewer |
| **F5** | Test Runner |
| **F10** | Quit |
| **Ctrl+C** | Quit |
| **R** | Run/Rerun (context-dependent) |
| **Q** | Back/Quit (context-dependent) |

## Architecture

```
freya/ui/
├── __init__.py              # Package initialization
├── app.py                   # Main FreyaApp and screens routing
│
├── screens/                 # Screen implementations
│   ├── system_checks.py     # ✅ System health checks
│   ├── config_screen.py     # 🚧 Configuration editor
│   ├── chat_screen.py       # 🚧 Chat interface
│   ├── logs_screen.py       # 🚧 Log viewer
│   └── tests_screen.py      # 🚧 Test runner
│
├── checks/                  # System check modules
│   ├── __init__.py          # BaseSystemCheck class
│   ├── python_check.py      # Python version check
│   ├── ollama_check.py      # Ollama connection
│   ├── whisper_check.py     # Whisper STT
│   ├── audio_check.py       # Mic/speaker checks
│   ├── tts_check.py         # TTS engine check
│   └── memory_check.py      # ChromaDB check
│
├── widgets/                 # Reusable UI components
│   └── __init__.py
│
├── themes/                  # Textual CSS themes
│   └── dark.tcss            # Dark theme (default)
│
└── utils/                   # UI utilities
    └── __init__.py
```

## Design Principles

### Modern Standards
- **Async/await throughout**: All checks and operations are async
- **Type hints**: Full type annotations with TYPE_CHECKING guards
- **Dataclasses**: Structured data with CheckResult and CheckStatus
- **Enums**: Type-safe status values
- **Protocol classes**: Duck typing where appropriate
- **Context managers**: Proper resource cleanup

### UI/UX
- **Responsive design**: Works in any terminal size
- **Keyboard-first**: All actions accessible via shortcuts
- **Real-time updates**: Live status changes without refresh
- **Color-coded feedback**: Green (success), Yellow (warning), Red (error)
- **Helpful error messages**: Every failure includes a fix suggestion
- **Non-blocking**: UI stays responsive during long operations

### Integration
- **Config-driven**: Reads from existing `config/default.yaml`
- **Standalone mode**: Can run independently for system monitoring
- **MessageBus ready**: Prepared for live coordinator integration
- **Log integration**: Can display real-time logs from running Freya

## Development Status

**Branch**: `feature/textual-tui`

**Phase 1: Foundation** ✅ **COMPLETE**
- [x] Base structure and theme
- [x] System check infrastructure
- [x] SystemChecksScreen with DataTable
- [x] Main app with routing
- [x] Entry point (main_ui.py)

**Phase 2: Configuration** 🚧 **IN PROGRESS**
- [ ] Tree navigation widget
- [ ] Config editor forms
- [ ] YAML read/write
- [ ] Live reload

**Phase 3: Chat & Logs** 🔜 **PLANNED**
- [ ] Chat bubble widgets
- [ ] MessageBus bridge
- [ ] Log handler
- [ ] Filter widgets

**Phase 4: Testing** 🔜 **PLANNED**
- [ ] Pytest integration
- [ ] Test suite tree
- [ ] Progress tracking
- [ ] Report generation

## Testing the TUI

```bash
# Run TUI
python main_ui.py

# Navigate with F-keys
# Press F1 to see System Checks
# Press R to rerun checks
# Press Q or F10 to quit
```

## Integration with Main App

Two modes of operation:

### 1. Standalone Mode (Current)
```bash
python main_ui.py  # Pure UI, no voice assistant running
```
Use for:
- System health monitoring
- Configuration management
- Viewing logs after the fact

### 2. Integrated Mode (Future)
```bash
python main.py --ui  # Launch UI alongside coordinator
```
Use for:
- Live chat monitoring
- Real-time log streaming
- Dynamic config updates
- Test execution while Freya runs

## Contributing

See the main README.md for contribution guidelines.

## Acknowledgments

Built with [Textual](https://textual.textualize.io/) - A TUI framework for Python inspired by modern web development.
