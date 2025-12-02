# Freya Cleanup & Enhancement Plan

**Status**: 57% functionality complete | 3 critical issues | 11 untested features
**Goal**: Production-ready voice assistant with robust agent architecture
**Release Target**: **v0.4.0** - Stable Agent Architecture Release

---

## 🎯 Release Milestone: v0.4.0

**Theme**: "Stable Foundation"
**Target Date**: 4 weeks from start
**Scope**: Bug-free core + tested baseline + clean architecture

### Release Criteria (Must have ALL):
- ✅ **Zero critical bugs** (Phase 1 complete)
- ✅ **100% core feature testing** (Phase 2 complete)
- ✅ **Module interfaces documented** (Phase 3 design complete)
- ✅ **CI/CD enforced** (Phase 5 complete)
- ✅ **80%+ test coverage** (Integration tests passing)

### Optional (Nice-to-have for v0.4.0):
- 🎯 Hardware abstraction layer (Phase 3)
- 🎯 Smart agent routing (Phase 4)
- 🎯 Load-balanced tools (Phase 4)

### Deferred to v0.5.0:
- ⏭️ Home Assistant integration (Phase 6)
- ⏭️ Advanced multi-model pipeline (Phase 4)
- ⏭️ Comprehensive docs (Phase 7)

---

## 🚨 Phase 1: Critical Bug Fixes (IMMEDIATE - 1-2 days)
**Blocking**: Core functionality broken, user-facing crashes

### P0 - Must Fix Now
1. **Fix config display crash** (Option 3)
   - **Issue**: `'SpeechToTextConfig' object has no attribute 'model_id'`
   - **Impact**: Startup menu crashes, blocks config inspection
   - **Fix**: Add missing `model_id` property or update config display logic
   - **Estimated**: 30 mins
   - **Files**: `freya/utils/startup_system.py`, `freya/core/config.py`

2. **Fix file listing tool output injection**
   - **Issue**: Tool executes correctly, LLM ignores actual output and hallucinates
   - **Impact**: File operations unreliable, user trust broken
   - **Root cause**: Context injection not working OR prompt not emphasizing tool results
   - **Fix**: Debug ToolExecutorAgent → DialogAgent message flow
   - **Estimated**: 2-3 hours
   - **Files**: `freya/agents/tool_executor_agent.py`, `freya/agents/dialog_agent.py`

3. **Implement web scraper functionality**
   - **Issue**: Returns "I cannot scrape" error
   - **Impact**: Web research capability completely missing
   - **Fix**: Implement or enable existing web scraper tool
   - **Estimated**: 1-2 hours
   - **Files**: `freya/tools/web_scraper.py`

**Success Criteria**: All startup options work, file tools reliable, web scraper functional

---

## ✅ Phase 2: Core Feature Testing (HIGH - 2-3 days)
**Blocking**: Need verified baseline before adding features

### P1 - Test Existing Functionality
4. **Test and fix file read/write operations**
   - Test: `read_file`, `write_file`, `append_to_file` tools
   - Verify: Permissions, error handling, path validation
   - Document: Success/failure patterns
   - **Estimated**: 3-4 hours

5. **Test voice mode end-to-end**
   - Test: Wake word detection ("Hey Freya")
   - Test: STT accuracy (Faster Whisper)
   - Test: ElevenLabs TTS playback
   - Test: Voice command processing
   - Test: Natural language exit phrases
   - **Estimated**: 4-6 hours (requires hardware setup)

6. **Test system info and performance tools**
   - Test: `system_info`, `cpu_usage`, `memory_usage` tools
   - Verify: Accurate metrics, no performance degradation
   - **Estimated**: 1 hour

**Success Criteria**: All 9 tools working + voice mode functional

---

## 🔒 FREEZE RULE: Phase 1-2 Stabilization Period

**CRITICAL**: During Phase 1-2, the following rules apply:

### ❌ FORBIDDEN:
- **NO new features** - Don't add capabilities, only fix existing ones
- **NO new modules** - Don't create new directories or subsystems
- **NO architecture changes** - Don't refactor core systems
- **NO dependency additions** - Don't add new libraries to requirements.txt
- **NO scope creep** - "Just one more tool" → NO

### ✅ ALLOWED:
- **Bug fixes only** - Fix crashes, errors, broken functionality
- **Testing** - Add tests for existing features
- **Documentation** - Document what already exists
- **Configuration** - Tweak settings, timeouts, thresholds
- **Logging** - Add debug output to understand issues

### Why This Matters:
- **Focus**: Fix what's broken before building new things
- **Quality**: 100% working baseline > 50% working features
- **Velocity**: Switching contexts kills productivity
- **Trust**: Users need reliability before features

**Enforcement**: Code reviews MUST reject PRs that violate freeze rules during Phase 1-2.

---

## 🏗️ Phase 3: Architecture Foundation (HIGH - 3-5 days)
**Blocking**: Needed before advanced features, prevents future refactors

### P1 - Module Interfaces & Abstraction
7. **Design strict module interface plan**
   - **Vision Module**
     - Interface: `capture()`, `detect_faces()`, `describe_scene()`, `stream_rtsp()`
     - Implementations: OpenCV, face_recognition, YOLO (future)
     - Config: Camera credentials, facial recognition paths

   - **Memory Module**
     - Interface: `store()`, `retrieve()`, `search()`, `consolidate()`
     - Implementations: ChromaDB (current), SQLite backup, Redis (future)
     - Config: Vector dimensions, retrieval count, consolidation threshold

   - **Audio Module**
     - Interface: `listen()`, `speak()`, `detect_wake_word()`, `list_devices()`
     - Implementations: Faster Whisper (STT), ElevenLabs/Piper (TTS), Wake detector
     - Config: Device IDs, models, voice settings

   - **IoT Module** (new)
     - Interface: `discover_devices()`, `send_command()`, `get_state()`
     - Implementations: Home Assistant API, MQTT, direct integrations
     - Config: HA URL, API token, device mappings

   - **Estimated**: 4-6 hours (design + document)
   - **Output**: `docs/MODULE_INTERFACES.md`

8. **Implement hardware abstraction layer**
   - **Purpose**: Decouple hardware dependencies from business logic
   - **Audio HAL**: Abstract sounddevice, pyaudio dependencies
   - **Camera HAL**: Abstract OpenCV, RTSP, ONVIF dependencies
   - **Benefit**: Easier testing (mocks), platform portability, device swapping
   - **Estimated**: 6-8 hours
   - **Files**: `freya/hardware/audio_hal.py`, `freya/hardware/camera_hal.py`

9. **Add unified logging instrumentation**
   - **Purpose**: Make debugging 10× easier across all modules

   - **Unified Logging Format**:
     ```python
     [2025-12-02 14:32:15.234] [DialogAgent] [INFO] Generated response (142 tokens, 2.3s)
     [2025-12-02 14:32:15.456] [ToolExecutor] [DEBUG] Executing tool: time_tool
     [2025-12-02 14:32:15.789] [MemoryAgent] [ERROR] ChromaDB connection failed
     ```

   - **Log Levels** (following Python stdlib):
     - `DEBUG`: Tool execution details, agent events, message flow
     - `INFO`: User interactions, model switches, config changes
     - `WARNING`: Timeouts, fallbacks, degraded performance
     - `ERROR`: Tool failures, API errors, agent crashes
     - `CRITICAL`: System-wide failures, data corruption

   - **Module-Level Log Routing**:
     ```python
     # Each module gets its own logger
     freya.agents.dialog → logs/agents_dialog.log
     freya.tools.web_search → logs/tools_web_search.log
     freya.memory.chroma_store → logs/memory_chroma.log
     freya.voice.stt → logs/voice_stt.log
     ```

   - **Timestamped Piped Logs**:
     - All logs → `logs/freya_YYYYMMDD_HHMMSS.log` (master log)
     - Module-specific → `logs/{module}_{date}.log` (filtered)
     - Console output: INFO and above (no DEBUG spam)
     - File output: DEBUG and above (everything)

   - **Structured Logging** (JSON for parsing):
     ```json
     {
       "timestamp": "2025-12-02T14:32:15.234Z",
       "module": "DialogAgent",
       "level": "INFO",
       "message": "Generated response",
       "context": {
         "tokens": 142,
         "duration_ms": 2300,
         "model": "llama3.2:3b"
       }
     }
     ```

   - **Log Rotation**:
     - Max file size: 10MB
     - Keep last 7 days
     - Compress old logs (gzip)

   - **Performance Impact**:
     - Use lazy evaluation: `logger.debug("Result: %s", expensive_fn)` (only calls expensive_fn if DEBUG enabled)
     - Async logging to avoid blocking

   - **Implementation**:
     ```python
     # freya/core/logger.py
     import logging
     from pathlib import Path

     def get_logger(module_name: str) -> logging.Logger:
         logger = logging.getLogger(f"freya.{module_name}")
         # ... setup handlers, formatters, rotation
         return logger
     ```

   - **Estimated**: 4-5 hours
   - **Files**:
     - `freya/core/logger.py` (central logging config)
     - Update all modules to use `get_logger(__name__)`
     - `config/default.yaml` (add logging section)

   - **Debugging Benefits**:
     - Trace full message flow through agents
     - Identify slow tools/models
     - Catch silent failures
     - Reproduce bugs from logs

**Success Criteria**: Clear module contracts, hardware dependencies isolated, comprehensive logging

---

## 🧠 Phase 4: Agent Intelligence (MEDIUM - 4-6 days)
**Dependency**: Phase 3 interfaces designed

### P2 - Smart Orchestration
10. **Review and enhance agent routing system**
    - **Current**: MessageBus pub/sub, agents subscribe to events
    - **Enhancements**:
      - Add agent priority levels (critical, normal, background)
      - Implement agent health monitoring (crash recovery)
      - Add event replay for failed agents
      - Create agent dependency graph
    - **Estimated**: 4-6 hours
    - **Files**: `freya/core/message_bus.py`, `freya/coordination/orchestration_coordinator.py`

11. **Implement model-switching orchestrator**
    - **Current State**: Dialog agent has basic escalation (llama3.2 → dolphin-mixtral)
    - **Enhancements**:
      - Formalize confusion detection metrics
      - Add model performance tracking (latency, quality scores)
      - Implement smart model selection (time-sensitive → fast model, reasoning → slow model)
      - Support 3-tier strategy: llama3.2:3b (fast) → dolphin-mixtral:8x7b (reasoning) → deepseek-coder-v2:16b-lite (code)
    - **Estimated**: 6-8 hours
    - **Files**: `freya/agents/dialog_agent.py`, `freya/core/model_selector.py` (new)

12. **Create load-balanced tool chain**
    - **Current**: Tools execute sequentially
    - **Enhancement**: Parallel tool execution when independent
      - Example: "What's the weather and time?" → execute both tools simultaneously
      - Tool dependency graph (file_read depends on file_list)
      - Timeout handling (kill slow tools, return partial results)
      - Resource limits (max 3 tools in parallel)
    - **Estimated**: 8-10 hours
    - **Files**: `freya/agents/tool_executor_agent.py`, `freya/tools/manager.py`

13. **Create unified pipeline for multi-model coordination**
    - **Goal**: Seamless handoff between models for complex tasks
    - **Example Flow**:
      1. User: "Search for Python async tutorials and summarize the top 3"
      2. llama3.2:3b detects tools needed (web_search)
      3. Execute web_search tool (3 results)
      4. Escalate to dolphin-mixtral:8x7b for summarization (needs reasoning)
      5. Return unified response
    - **Estimated**: 6-8 hours
    - **Files**: `freya/coordination/multi_model_pipeline.py` (new)

**Success Criteria**: Smart model routing, parallel tools, resilient agent system

---

## 🧪 Phase 5: Testing Infrastructure (MEDIUM - 2-3 days)
**Dependency**: Phase 2 complete (known baseline)

### P2 - Test Coverage
14. **Add integration tests**
    - **Agent Coordination Tests**:
      - Test MessageBus event flow (wake.detected → dialog.request → memory.stored)
      - Test agent crash recovery
      - Test context injection (memory → dialog)

    - **Tool Execution Tests**:
      - Test all 9 tools with real inputs
      - Test tool timeout handling
      - Test parallel tool execution

    - **Model Escalation Tests**:
      - Test confusion detection triggering escalation
      - Test model fallback on failure

    - **End-to-End Tests**:
      - Test full conversation flow (text mode)
      - Test wake word → response → memory storage (voice mode)
      - Test multi-turn conversations with context

    - **Estimated**: 10-12 hours
    - **Files**: `tests/test_integration_*.py`

15. **Set up CI/CD checks**
    - **GitHub Actions Workflow**:
      - Lint: ruff check (block on errors)
      - Type check: mypy (block on errors)
      - Unit tests: pytest (block on failures)
      - Integration tests: pytest integration/ (block on failures)
      - Security: pip-audit (warn on vulnerabilities)

    - **Pre-commit Hooks**:
      - Format: ruff format
      - Lint: ruff check --fix
      - Type hints: mypy

    - **Branch Protection**:
      - Require CI pass before merge to main
      - Require code review for PRs

    - **Estimated**: 3-4 hours
    - **Files**: `.github/workflows/ci.yml`, `.pre-commit-config.yaml`

**Success Criteria**: 80%+ test coverage, CI blocking bad merges

---

## 🏠 Phase 6: Home Automation (LOW - 3-4 days)
**Dependency**: Phase 3 IoT interface designed

### P3 - IoT Integration
16. **Add Home Assistant integration**
    - **Features**:
      - Auto-discover HA entities (lights, switches, sensors)
      - Send commands via HA REST API ("turn off bedroom lights")
      - Query state ("is the front door locked?")
      - Subscribe to HA events via WebSocket (motion detected)
      - Context-aware commands ("turn off the lights" → use room context from facial recognition/camera)

    - **Components**:
      - `freya/iot/home_assistant_client.py` - HA API wrapper
      - `freya/agents/iot_agent.py` - Agent for IoT coordination
      - `freya/tools/iot_control.py` - Tool for user commands

    - **Config**:
      ```yaml
      iot:
        home_assistant:
          enabled: true
          url: "http://homeassistant.local:8123"
          api_token: "your_long_lived_token"
          auto_discover: true
      ```

    - **Estimated**: 8-10 hours
    - **Files**: `freya/iot/` (new directory)

**Success Criteria**: Voice commands control HA devices, state queries work

---

## 📚 Phase 7: Documentation (LOW - 2-3 days)
**Dependency**: Phase 3-6 complete

### P3 - Knowledge Base
17. **Expand module documentation**
    - **Vision Module** (`docs/VISION_MODULE.md`):
      - Facial recognition setup guide
      - Camera integration guide (RTSP, ONVIF)
      - Troubleshooting common camera issues

    - **Memory Module** (`docs/MEMORY_MODULE.md`):
      - ChromaDB architecture
      - Fact extraction patterns
      - Context consolidation strategy
      - Backup/restore procedures

    - **Audio Module** (`docs/AUDIO_MODULE.md`):
      - Device selection guide
      - STT model comparison (Faster Whisper vs alternatives)
      - TTS voice comparison (ElevenLabs vs Piper)
      - Multi-channel audio coordination

    - **Tools Module** (`docs/TOOLS_MODULE.md`):
      - Built-in tools reference
      - Custom tool creation guide
      - Tool security considerations

    - **Agent System** (`docs/AGENT_ARCHITECTURE.md`):
      - MessageBus event catalog
      - Agent lifecycle management
      - Creating custom agents
      - Agent debugging guide

    - **Estimated**: 6-8 hours
    - **Files**: `docs/*.md`

**Success Criteria**: New contributors can understand architecture, users can troubleshoot

---

## 📊 Summary & Timeline

### Priority Breakdown
| Priority | Items | Estimated Time | Rationale |
|----------|-------|----------------|-----------|
| **P0** (Critical) | 3 | 4-6 hours | Blocks basic functionality |
| **P1** (High) | 6 | 22-29 hours | Foundation for all future work |
| **P2** (Medium) | 6 | 30-36 hours | Enhanced intelligence & quality |
| **P3** (Low) | 2 | 14-18 hours | Nice-to-have features |

**Total**: 17 items | 70-89 hours (~2-3 weeks with buffer)

### Recommended Execution Order
**Week 1** (Foundation):
- Days 1-2: Phase 1 (Critical Bugs) ✅ REQUIRED
- Days 3-5: Phase 2 (Core Testing) ✅ REQUIRED

**Week 2** (Architecture):
- Days 1-3: Phase 3 (Interfaces & HAL) ✅ REQUIRED
- Days 4-5: Phase 5 (Testing Infrastructure) ✅ REQUIRED

**Week 3** (Intelligence):
- Days 1-5: Phase 4 (Agent Enhancements)

**Week 4** (Polish):
- Days 1-3: Phase 6 (Home Assistant)
- Days 4-5: Phase 7 (Documentation)

### Dependencies Graph
```
Phase 1 (Bugs) ──┬──> Phase 2 (Testing) ──> Phase 5 (CI/CD)
                 │                              ↓
                 └──> Phase 3 (Interfaces) ──> Phase 4 (Agents) ──> Phase 7 (Docs)
                                 ↓
                            Phase 6 (IoT)
```

### Success Metrics
- ✅ **0 Critical Bugs**: All startup options work, no crashes
- ✅ **100% Tool Coverage**: All 9 tools tested and working
- ✅ **Voice Mode Functional**: End-to-end voice interaction working
- ✅ **80% Test Coverage**: Unit + integration tests
- ✅ **CI/CD Enforced**: No merges without passing tests
- ✅ **Module Interfaces Documented**: Clear contracts for Vision/Memory/Audio/IoT
- ✅ **Smart Orchestration**: Model escalation + parallel tools working
- 🎯 **Stretch Goal**: Home Assistant integration live

---

## Quick Reference: What to Work On Today

### If you have 2 hours:
→ **Fix config crash + file listing bug** (Phase 1, items 1-2)

### If you have 4 hours:
→ **Complete Phase 1** (all critical bugs fixed)

### If you have 8 hours:
→ **Phase 1 + start Phase 2** (bugs + voice mode testing)

### If you have 1 week:
→ **Phases 1-3** (bugs + testing + architecture foundation)

---

## Notes
- **Parallelization**: Phase 3 (interfaces) and Phase 5 (CI/CD) can run in parallel after Phase 2
- **Staffing**: If multiple devs, split Phase 2 (testing) and Phase 3 (interfaces)
- **Risk**: Phase 4 (agents) is most complex, allocate buffer time
- **Flexibility**: Phase 6 (IoT) and Phase 7 (docs) can be deferred if timeline pressure

**Last Updated**: 2025-12-02
**Status**: Planning phase, awaiting approval to begin Phase 1
