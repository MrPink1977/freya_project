# Freya Comprehensive Testing Guide

This guide will walk you through testing ALL of Freya's capabilities step by step.

## Prerequisites

### 1. Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install dev dependencies (optional)
pip install -r requirements-dev.txt
```

### 2. Start Ollama

```bash
# In a separate terminal
ollama serve

# Pull a model if you haven't
ollama pull llama3.2:3b  # Or your preferred model
```

### 3. Configure Freya

```bash
# Copy example config
cp config/default.yaml config/my_config.yaml

# Edit if needed (optional)
nano config/my_config.yaml
```

---

## Test Phase 1: Tool System (5 minutes)

### Quick Tool Demo
```bash
python demo_tools.py
```

**Expected Output:** All 11 tools should execute successfully
- ✓ Time tools (get time, get date, calculate time)
- ✓ Calculator (math expressions)
- ✓ File operations (list files)
- ✓ System info
- ✓ Web search (if internet available)

### Comprehensive System Test
```bash
python test_freya_comprehensive.py
```

**Expected Results:**
- ✓ All modules import
- ✓ Tool Manager: 11 tools initialized
- ✓ Tool Tests: 10/10 passed
- ✓ Configuration loaded
- ✓ Context management working

---

## Test Phase 2: Freya Integration - TEXT MODE (10 minutes)

### Start Freya in Text Mode

```bash
# Start in text mode (easier for testing)
FREYA_STARTUP_MODE=normal python main.py
```

Or if prompted, choose **Text mode** (press 't' or just Enter).

### Test 1: Basic Conversation
```
You: Hello Freya
Expected: Freya responds with greeting
```

### Test 2: Time Tool
```
You: What time is it?
Expected: [Getting current time...] followed by current time in UTC
```

### Test 3: Date Tool
```
You: What date is today?
Expected: [Getting current date...] followed by current date
```

### Test 4: Calculator
```
You: Calculate 25 * 4
Expected: [Calculating...] followed by "100"
```

```
You: What is sqrt(144) + 10?
Expected: Calculator returns "22"
```

### Test 5: File Operations
```
You: List files in the current directory
Expected: [Listing files...] followed by file list
```

### Test 6: System Information
```
You: Show me system information
Expected: OS, Python version, disk space info
```

### Test 7: Web Search (if internet available)
```
You: Search for Python programming tutorials
Expected: [Searching the web...] followed by search results
```

### Test 8: Memory
```
You: Remember that my favorite color is blue
Expected: Freya confirms

You: What's my favorite color?
Expected: Freya recalls "blue"
```

### Test 9: Conversation Context
```
You: My name is [Your Name]
Expected: Freya acknowledges

You: What did I just tell you?
Expected: Freya remembers your name
```

### Exit
```
You: exit
```

---

## Test Phase 3: Freya Integration - VOICE MODE (15 minutes)

**Note:** Requires microphone and speakers

### Start in Voice Mode

```bash
python main.py
```

Choose Voice mode (press 'v' or just Enter).

### Test 1: Wake Word Detection
- Say: "Hey Freya"
- Expected: Tone plays, "Listening..." appears

### Test 2: Voice Commands

Try each of these after wake word:

```
"Hey Freya, what time is it?"
"Hey Freya, calculate two plus two"
"Hey Freya, what date is today?"
"Hey Freya, list files"
"Hey Freya, search for artificial intelligence"
```

### Test 3: Session Window
After first command, try speaking again within 8 seconds **without** wake word:
```
[After Freya responds]
"And what about the weather?" (no wake word needed if within 8s)
```

### Test 4: Hotkeys
- Press **Ctrl+T** to toggle between voice and text modes
- Press **Space** to interrupt Freya while speaking

### Exit
Say: "Hey Freya, exit"

---

## Test Phase 4: Camera Integration (Optional, 10 minutes)

**Requirements:** IP camera with RTSP support

### Configure Camera

Edit `config/my_camera_config.yaml`:
```yaml
camera_ip: "192.168.0.22"
camera_user: "admin"
camera_pass: "your_password"
```

### Test Face Detection
```bash
export REOLINK_CAM_PASS="your_password"
python demo_simple_face_detection.py
```

Expected: Detects faces in camera feed

### Test Face Recognition (if setup)
```bash
# Add known faces first
mkdir -p data/faces/YourName
cp your_photo.jpg data/faces/YourName/

# Run recognition
python demo_facial_recognition.py
```

Expected: Recognizes known faces

---

## Test Phase 5: Advanced Features (15 minutes)

### 1. Memory Persistence
```bash
# Session 1
python main.py
You: Remember my birthday is December 25th
You: exit

# Session 2 (new run)
python main.py
You: When is my birthday?
Expected: Freya recalls "December 25th"
```

### 2. Multi-turn Conversation
```
You: Hey Freya
You: Calculate 10 plus 5
Freya: [responds "15"]
You: Now multiply that by 2
Expected: Freya understands context and says "30"
```

### 3. Complex Queries
```
You: Search for today's weather and tell me if I need an umbrella
Expected: Uses web search + reasoning
```

### 4. File + Calculator Combo
```
You: List Python files in the freya/tools directory
[Freya lists files]
You: How many files are there?
Expected: Freya counts from previous result
```

---

## Troubleshooting

### Ollama Not Responding
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start if not running
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Audio Issues
```bash
# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Update device IDs in config/default.yaml if needed
```

### Tools Not Working
```bash
# Test tools individually
python demo_tools.py

# Check tool manager
python -c "from freya.tools import ToolManager; m = ToolManager(); print(len(m.list_tools()))"
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## Success Criteria

### ✅ Minimum Passing Tests
- [ ] All 11 tools execute successfully (demo_tools.py)
- [ ] Text mode conversation works
- [ ] At least 5 tool integrations work (time, date, calc, files, system)
- [ ] Memory persists across sessions
- [ ] Ollama responds to queries

### ✅ Full Feature Pass
- [ ] All tool tests pass
- [ ] Voice mode with wake word works
- [ ] Hotkey toggling works
- [ ] Web search functional
- [ ] Camera integration (if hardware available)
- [ ] Multi-turn conversations maintain context
- [ ] Memory recall accurate

---

## Performance Benchmarks

**Tool Response Times (expected):**
- Calculator: < 0.1s
- Time/Date: < 0.1s
- File ops: < 0.5s
- System info: < 0.2s
- Web search: 1-3s
- Web scraper: 2-5s

**Conversation Flow:**
- Wake word detection: < 1s
- Speech-to-text: 1-3s
- LLM response: 2-10s (depends on model)
- Text-to-speech: 1-3s

---

## Next Steps After Testing

1. **Customize Tools**: Add your own tools to `freya/tools/`
2. **Tune Memory**: Adjust memory settings in config
3. **Add Camera**: Set up facial recognition
4. **Voice Training**: Improve wake word sensitivity
5. **Extend Capabilities**: Add home automation, email, etc.

---

## Getting Help

- Check logs: Freya logs to console in diagnostic mode
- Enable diagnostic mode: `--startup-mode diagnostic`
- Review docs: `docs/TOOLS.md` and `docs/TOOL_INTEGRATION.md`
- Test individual components before full integration

---

**Happy Testing! 🚀**
