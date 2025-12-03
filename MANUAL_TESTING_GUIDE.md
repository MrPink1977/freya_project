# Freya TTS/STT Manual Testing Guide

**Date:** December 2, 2025  
**Version:** 1.0  
**Purpose:** Verify ElevenLabs MCP integration and dual-Whisper STT architecture

---

## Prerequisites

### System Requirements

- ✅ **Operating System:** Windows, macOS, or Linux
- ✅ **Python:** 3.11+
- ✅ **Audio Hardware:** 
  - Microphone (for STT testing)
  - Speakers/headphones (for TTS testing)
- ✅ **Internet Connection:** Required for ElevenLabs MCP (cloud-based)

### Software Requirements

- ✅ **Ollama:** Installed and running
- ✅ **Git:** For pulling latest changes
- ✅ **PortAudio:** For audio playback

---

## Part 1: Setup and Preparation

### Step 1.1: Pull Latest Changes

```bash
# Navigate to Freya project directory
cd /path/to/freya_project

# Pull latest changes from main
git pull origin main

# Verify you have the latest commit (3bfe14e)
git log -1 --oneline
# Should show: 3bfe14e feat: Add ElevenLabs MCP TTS integration
```

**Expected Output:**
```
remote: Enumerating objects: 19, done.
remote: Counting objects: 100% (19/19), done.
...
Already up to date.
```

**✅ Pass Criteria:** Git shows commit `3bfe14e` or later

---

### Step 1.2: Activate Virtual Environment

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

# Verify Python version
python --version
# Should be 3.11+
```

**Expected Output:**
```
Python 3.11.x
```

**✅ Pass Criteria:** Python 3.11 or higher

---

### Step 1.3: Install Dependencies

```bash
# Install all requirements including MCP
pip install -r requirements.txt

# Verify elevenlabs-mcp is installed
pip show elevenlabs-mcp
```

**Expected Output:**
```
Name: elevenlabs-mcp
Version: 0.9.0
Summary: ElevenLabs MCP Server
...
```

**✅ Pass Criteria:** elevenlabs-mcp version 0.9.0 installed

---

### Step 1.4: Install System Audio Libraries

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev libportaudio2 ffmpeg
```

#### macOS
```bash
brew install portaudio ffmpeg
```

#### Windows
```bash
# Usually included with Python
# If issues, install: https://people.csail.mit.edu/hubert/pyaudio/
```

**✅ Pass Criteria:** No errors during installation

---

### Step 1.5: Configure Environment Variables

```bash
# Check if .env file exists
ls -la .env

# If not exists, create it
nano .env  # or use your preferred editor
```

**Add to `.env` file:**
```bash
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=3fec1d7b5b1968f7d9e690e2425b16730a4daaab6d30fc2e676e7532b98ac70b
ELEVENLABS_VOICE_ID=AXdMgz6evoL7OPd7eU12
```

**Verify:**
```bash
cat .env | grep ELEVENLABS
```

**Expected Output:**
```
ELEVENLABS_API_KEY=3fec1d7b5b...
ELEVENLABS_VOICE_ID=AXdMgz6evoL7OPd7eU12
```

**✅ Pass Criteria:** Both variables set correctly

---

### Step 1.6: Verify Audio Devices

```bash
# Run Python script to list audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

**Expected Output:**
```
  0 Built-in Microphone, Core Audio (2 in, 0 out)
> 1 Built-in Output, Core Audio (0 in, 2 out)
...
```

**✅ Pass Criteria:** At least one input and one output device listed

---

## Part 2: MCP Communication Testing

### Step 2.1: Test MCP Server Installation

```bash
# Run simple MCP communication test
python test_mcp_simple.py
```

**Expected Output:**
```
🎤 Testing ElevenLabs MCP Server Communication
============================================================
API Key: 3fec1d7b5b...32b98ac70b
Voice ID: AXdMgz6evoL7OPd7eU12
============================================================

✅ Found MCP server: /path/to/elevenlabs_mcp/server.py

1️⃣  Testing MCP server initialization...
   Starting MCP server process...
   Sending request: tools/list
✅ MCP server responded successfully
   Found 20 tools:
     - text_to_speech
     - speech_to_text
     - list_voices
     - get_voice
     - create_voice
     ... and 15 more

============================================================
🎉 MCP server communication test PASSED!
============================================================
```

**✅ Pass Criteria:** 
- MCP server found
- Server responds successfully
- At least 15+ tools listed
- No errors or timeouts

**❌ Fail Scenarios:**
- "elevenlabs-mcp not installed" → Reinstall: `pip install elevenlabs-mcp==0.9.0`
- "ELEVENLABS_API_KEY not set" → Check `.env` file
- "MCP server timeout" → Check internet connection

---

### Step 2.2: Test MCP Text-to-Speech (Audio Output)

```bash
# Run full TTS test with audio playback
python test_elevenlabs_mcp.py
```

**Expected Output:**
```
🎤 Testing ElevenLabs MCP TTS Integration
============================================================
API Key: 3fec1d7b5b...32b98ac70b
Voice ID: AXdMgz6evoL7OPd7eU12
============================================================

1️⃣  Initializing ElevenLabs MCP TTS...
✅ ElevenLabs MCP TTS initialized successfully

2️⃣  Testing text-to-speech...
Text: Hello! This is a test of the ElevenLabs MCP integration...

🔊 Speaking...
[You should HEAR audio playing through speakers]
✅ Speech completed successfully

3️⃣  Testing short phrase...
[You should HEAR "Integration test successful!"]
✅ Short phrase completed

============================================================
🎉 All tests passed! ElevenLabs MCP TTS is working!
============================================================
```

**✅ Pass Criteria:**
- Initialization successful
- **AUDIO PLAYS** through speakers (you hear the voice)
- Both test phrases complete without errors
- Voice quality is clear and natural

**❌ Fail Scenarios:**
- "PortAudio library not found" → Install portaudio (Step 1.4)
- "No audio output" → Check speaker volume, verify audio device
- "TextToSpeechError" → Check API key, internet connection
- "Invalid API key" → Verify API key in `.env` file

---

## Part 3: Freya Integration Testing

### Step 3.1: Configure TTS Engine

```bash
# Edit configuration file
nano config/default.yaml

# Find the TTS section and set engine to elevenlabs_mcp:
```

**Configuration:**
```yaml
tts:
  engine: "elevenlabs_mcp"  # Options: "piper", "elevenlabs", "elevenlabs_mcp"
  
  elevenlabs:
    api_key: ""  # Leave empty - uses .env
    voice_id: "AXdMgz6evoL7OPd7eU12"
    model: "eleven_turbo_v2_5"  # Fast model for low latency
    stability: 0.5
    similarity_boost: 0.75
    style: 0.0
    use_speaker_boost: true
```

**Save and verify:**
```bash
grep -A 10 "^tts:" config/default.yaml
```

**✅ Pass Criteria:** `engine: "elevenlabs_mcp"` is set

---

### Step 3.2: Test Text Mode (No Voice)

```bash
# Run Freya in text mode
python main.py --mode text
```

**Expected Output:**
```
[System checks running...]
✓ Ollama connection
✓ Models available
✓ Configuration loaded
...

Starting Freya in text mode...
You: 
```

**Test Interaction:**
```
You: Hello Freya, what time is it?
Freya: [Response with current time]

You: Tell me a joke
Freya: [Tells a joke]

You: exit
```

**✅ Pass Criteria:**
- Freya starts without errors
- Responses are coherent and contextual
- No TTS errors in text mode
- Clean exit on "exit" command

**❌ Fail Scenarios:**
- Ollama connection error → Start Ollama: `ollama serve`
- Model not found → Pull model: `ollama pull llama3.2:3b`
- Configuration error → Check `config/default.yaml` syntax

---

### Step 3.3: Test Voice Mode (TTS Only)

```bash
# Run Freya in voice mode
python main.py --mode voice
```

**Expected Output:**
```
[System checks running...]
✓ Ollama connection
✓ Models available
✓ Configuration loaded
✓ Audio devices detected
✓ TTS engine initialized: elevenlabs_mcp
✓ STT engine initialized: faster-whisper
✓ Wake word detector initialized

Starting Freya in voice mode...
Listening for wake word: "Hey, Freya"...
```

**Test Interaction (Type, Don't Speak Yet):**

1. **Press Ctrl+C to skip wake word**
2. **Type:** "What time is it?"
3. **Listen:** Freya should SPEAK the response using ElevenLabs MCP voice
4. **Verify:** Voice is clear, natural, and matches your configured voice ID

**✅ Pass Criteria:**
- Voice mode starts successfully
- TTS engine shows "elevenlabs_mcp"
- **AUDIO PLAYS** when Freya responds
- Voice quality is high (ElevenLabs quality)
- No audio glitches or errors

**❌ Fail Scenarios:**
- "TTS initialization failed" → Check `.env` API key
- "No audio output" → Check speakers, audio device selection
- "MCP server error" → Check internet connection
- Robotic/low quality voice → Verify using elevenlabs_mcp, not piper

---

### Step 3.4: Test Wake Word Detection (STT)

**Still in voice mode from Step 3.3:**

1. **Say:** "Hey, Freya"
2. **Wait:** Wake word should be detected
3. **Say:** "What's the weather like?"
4. **Listen:** Freya should respond with speech

**Expected Console Output:**
```
Listening for wake word: "Hey, Freya"...
Wake word detected! Listening...
Transcription: "What's the weather like?"
[Freya processes and responds]
🔊 Speaking response...
```

**✅ Pass Criteria:**
- Wake word "Hey, Freya" is detected
- Your speech is transcribed correctly
- Freya responds with relevant answer
- **AUDIO PLAYS** for Freya's response
- Conversation feels natural

**❌ Fail Scenarios:**
- Wake word not detected → Check microphone, increase sensitivity
- Transcription incorrect → Check microphone quality, background noise
- No speech output → TTS issue (see Step 3.3)
- Freya doesn't understand → Check Ollama model, try rephrasing

---

### Step 3.5: Test Dual-Whisper Architecture

**Verify the two Whisper models are working:**

```bash
# While Freya is running, check logs
tail -f logs/freya.log
```

**Look for these log entries:**

```
[wake_word] Initialized Whisper model: tiny (wake word detection)
[stt] Initialized Whisper model: base (full transcription)
```

**Test Flow:**

1. **Say:** "Hey, Freya" → **Tiny model** detects wake word (~50ms)
2. **Say:** "Tell me about quantum physics" → **Base model** transcribes (~200ms)

**✅ Pass Criteria:**
- Two separate Whisper models initialized
- Wake word detection is fast (~50-100ms)
- Full transcription is accurate
- No model conflicts or errors

---

### Step 3.6: Test Engine Switching

**Test switching between TTS engines:**

**Option 1: Via Configuration**

```bash
# Stop Freya (Ctrl+C)
# Edit config
nano config/default.yaml

# Change engine to:
tts:
  engine: "piper"  # Local TTS

# Restart Freya
python main.py --mode text

# Type a message and verify Piper voice (lower quality, faster)
```

**Option 2: Via Runtime (Future Feature)**

```python
# In Freya conversation:
You: Switch to ElevenLabs MCP voice
Freya: [Should switch engines]
```

**✅ Pass Criteria:**
- Can switch between engines by editing config
- Each engine produces different voice quality
- No errors when switching
- Restart applies new engine correctly

---

## Part 4: Performance and Quality Testing

### Step 4.1: Latency Measurement

**Test TTS latency for each engine:**

```bash
# Create test script
cat > test_latency.py << 'EOF'
import time
from freya.voice.tts_elevenlabs_mcp import ElevenLabsMCPTTS
from freya.voice.tts import TextToSpeech
import os
from dotenv import load_dotenv

load_dotenv()

# Test ElevenLabs MCP
print("Testing ElevenLabs MCP latency...")
tts_mcp = ElevenLabsMCPTTS(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
)
start = time.time()
tts_mcp.speak("Testing latency")
mcp_latency = time.time() - start
print(f"ElevenLabs MCP: {mcp_latency:.2f}s")

# Test Piper (if available)
# ... add similar test for Piper
EOF

python test_latency.py
```

**Expected Results:**

| Engine | Latency | Quality |
|--------|---------|---------|
| Piper | ~100-200ms | ⭐⭐⭐ |
| ElevenLabs API | ~300-400ms | ⭐⭐⭐⭐⭐ |
| ElevenLabs MCP | ~500-700ms | ⭐⭐⭐⭐⭐ |

**✅ Pass Criteria:**
- ElevenLabs MCP latency < 1 second
- Voice quality is noticeably better than Piper
- No audio stuttering or glitches

---

### Step 4.2: Voice Quality Comparison

**Subjective quality test:**

1. **Test Phrase:** "The quick brown fox jumps over the lazy dog. How are you feeling today?"

2. **Test with Piper:**
   ```yaml
   tts:
     engine: "piper"
   ```

3. **Test with ElevenLabs MCP:**
   ```yaml
   tts:
     engine: "elevenlabs_mcp"
   ```

4. **Compare:**
   - Naturalness (human-like vs robotic)
   - Clarity (clear pronunciation)
   - Emotion (expressive vs monotone)
   - Accent (natural vs artificial)

**✅ Pass Criteria:**
- ElevenLabs MCP sounds significantly more natural
- Pronunciation is clear and accurate
- Emotional tone is present
- No artifacts or distortion

---

### Step 4.3: Stress Testing

**Test continuous operation:**

```bash
# Run Freya in voice mode
python main.py --mode voice

# Have a long conversation (10+ exchanges)
# Test various scenarios:
# - Short responses
# - Long responses (paragraphs)
# - Quick back-and-forth
# - Interruptions (Ctrl+M to stop speech)
```

**✅ Pass Criteria:**
- No memory leaks (check with `htop` or Task Manager)
- No audio degradation over time
- Consistent response quality
- Clean handling of interruptions

---

## Part 5: Error Handling and Edge Cases

### Step 5.1: Test API Key Failure

```bash
# Temporarily break API key
nano .env
# Change ELEVENLABS_API_KEY to invalid value

# Run test
python test_elevenlabs_mcp.py
```

**Expected Output:**
```
❌ Test failed: Invalid API key
```

**✅ Pass Criteria:**
- Clear error message
- No crash or hang
- Graceful failure

**Fix:**
```bash
# Restore correct API key
nano .env
```

---

### Step 5.2: Test Network Failure

```bash
# Disconnect internet
# Run Freya with elevenlabs_mcp

python main.py --mode text
You: Hello
```

**Expected Behavior:**
- Error message about network connectivity
- Freya should suggest switching to Piper (local)
- No crash

**✅ Pass Criteria:**
- Graceful error handling
- Helpful error messages
- System remains stable

---

### Step 5.3: Test Audio Device Failure

```bash
# Unplug speakers/headphones
# Run Freya

python main.py --mode voice
```

**Expected Behavior:**
- Warning about no audio output device
- Option to continue in text mode
- No crash

**✅ Pass Criteria:**
- Detects missing audio device
- Provides alternative (text mode)
- Clean error handling

---

## Part 6: Final Verification Checklist

### ✅ Setup Verification

- [ ] Git repository at commit `3bfe14e` or later
- [ ] Virtual environment activated
- [ ] `elevenlabs-mcp==0.9.0` installed
- [ ] PortAudio libraries installed
- [ ] `.env` file configured with API keys
- [ ] Audio devices detected

### ✅ MCP Integration

- [ ] MCP server communication test passes
- [ ] MCP TTS test produces audio output
- [ ] Voice quality is high (ElevenLabs quality)
- [ ] No MCP errors or timeouts

### ✅ Freya Integration

- [ ] Text mode works correctly
- [ ] Voice mode initializes successfully
- [ ] TTS engine shows "elevenlabs_mcp"
- [ ] Audio plays when Freya responds
- [ ] Wake word detection works
- [ ] Full speech transcription works

### ✅ Dual-Whisper STT

- [ ] Tiny model for wake word (fast)
- [ ] Base model for full transcription (accurate)
- [ ] Both models initialized in logs
- [ ] No model conflicts

### ✅ Engine Switching

- [ ] Can switch to Piper via config
- [ ] Can switch to ElevenLabs API via config
- [ ] Can switch to ElevenLabs MCP via config
- [ ] Each engine produces different output

### ✅ Performance

- [ ] ElevenLabs MCP latency < 1 second
- [ ] Voice quality noticeably better than Piper
- [ ] No audio stuttering or glitches
- [ ] Stable during long conversations

### ✅ Error Handling

- [ ] Invalid API key handled gracefully
- [ ] Network failure handled gracefully
- [ ] Missing audio device handled gracefully
- [ ] All errors have clear messages

---

## Troubleshooting Guide

### Issue: "PortAudio library not found"

**Solution:**
```bash
# Linux
sudo apt-get install portaudio19-dev libportaudio2

# macOS
brew install portaudio

# Then reinstall pyaudio
pip install --force-reinstall pyaudio
```

---

### Issue: "No audio output"

**Checklist:**
1. Check speaker volume
2. Verify audio device: `python -c "import sounddevice as sd; print(sd.query_devices())"`
3. Test system audio (play music)
4. Check Freya logs: `tail -f logs/freya.log`

---

### Issue: "MCP server timeout"

**Checklist:**
1. Check internet connection
2. Verify API key: `cat .env | grep ELEVENLABS`
3. Test API directly: `curl https://api.elevenlabs.io/v1/voices -H "xi-api-key: YOUR_KEY"`
4. Check firewall settings

---

### Issue: "Wake word not detected"

**Solutions:**
1. Increase microphone volume
2. Reduce background noise
3. Speak clearly and directly into microphone
4. Adjust sensitivity in `config/default.yaml`:
   ```yaml
   wake_detector:
     sensitivity: 0.7  # Increase to 0.8 or 0.9
   ```

---

## Success Criteria Summary

### Minimum Passing Requirements

1. ✅ **MCP Communication:** Test passes without errors
2. ✅ **Audio Output:** Can hear ElevenLabs voice
3. ✅ **Wake Word:** Detects "Hey, Freya"
4. ✅ **Transcription:** Accurately transcribes speech
5. ✅ **Integration:** Freya runs without crashes

### Optimal Performance

1. ✅ **Latency:** < 1 second for TTS
2. ✅ **Quality:** Natural, expressive voice
3. ✅ **Stability:** No errors during 10+ exchanges
4. ✅ **Error Handling:** Graceful failures with clear messages

---

## Next Steps After Testing

### If All Tests Pass ✅

**Congratulations!** Your Freya MCP integration is working perfectly.

**Next Module:** DuckDuckGo MCP for web search
- URL: https://hub.docker.com/mcp/server/duckduckgo/overview
- Integration guide coming next

### If Tests Fail ❌

1. **Document the failure:**
   - Which step failed?
   - What was the error message?
   - What were you doing when it failed?

2. **Check logs:**
   ```bash
   tail -100 logs/freya.log
   ```

3. **Review troubleshooting guide** (above)

4. **Report issue** with:
   - Step number that failed
   - Error message
   - Log excerpts
   - System info (OS, Python version, etc.)

---

## Testing Log Template

Use this template to document your testing:

```
=== FREYA TTS/STT MANUAL TESTING LOG ===
Date: _______________
Tester: _______________
System: _______________ (OS, Python version)

PART 1: SETUP
[ ] Step 1.1: Git pull - PASS/FAIL
[ ] Step 1.2: Virtual env - PASS/FAIL
[ ] Step 1.3: Dependencies - PASS/FAIL
[ ] Step 1.4: Audio libraries - PASS/FAIL
[ ] Step 1.5: Environment vars - PASS/FAIL
[ ] Step 1.6: Audio devices - PASS/FAIL

PART 2: MCP TESTING
[ ] Step 2.1: MCP communication - PASS/FAIL
[ ] Step 2.2: MCP TTS audio - PASS/FAIL

PART 3: FREYA INTEGRATION
[ ] Step 3.1: TTS config - PASS/FAIL
[ ] Step 3.2: Text mode - PASS/FAIL
[ ] Step 3.3: Voice mode TTS - PASS/FAIL
[ ] Step 3.4: Wake word STT - PASS/FAIL
[ ] Step 3.5: Dual-Whisper - PASS/FAIL
[ ] Step 3.6: Engine switching - PASS/FAIL

PART 4: PERFORMANCE
[ ] Step 4.1: Latency - PASS/FAIL (___ms)
[ ] Step 4.2: Voice quality - PASS/FAIL (rating: ___/5)
[ ] Step 4.3: Stress test - PASS/FAIL

PART 5: ERROR HANDLING
[ ] Step 5.1: API key failure - PASS/FAIL
[ ] Step 5.2: Network failure - PASS/FAIL
[ ] Step 5.3: Audio device failure - PASS/FAIL

OVERALL RESULT: PASS / FAIL

NOTES:
_______________________________________
_______________________________________
_______________________________________
```

---

**Good luck with testing! 🎉**

**Questions?** Review `docs/ELEVENLABS_MCP_INTEGRATION.md` for detailed technical information.
