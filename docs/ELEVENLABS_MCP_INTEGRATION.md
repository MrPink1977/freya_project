# ElevenLabs MCP Integration Guide

**Date:** December 2, 2025  
**Status:** Ready for Testing  
**Branch:** `main` (ready to merge)

---

## Overview

This document describes the integration of **ElevenLabs MCP server** with Freya's text-to-speech system. This provides an alternative TTS engine that uses the official ElevenLabs MCP protocol for voice synthesis.

### Why MCP Integration?

**Benefits:**
- ✅ **Official Protocol:** Uses Anthropic's Model Context Protocol standard
- ✅ **Future-Proof:** Compatible with MCP ecosystem and tools
- ✅ **Standardized:** Same interface as other MCP servers
- ✅ **Maintainable:** ElevenLabs maintains the MCP server
- ✅ **Extensible:** Easy to add more MCP-based services

**vs Direct API Integration:**
- Direct API (`tts_elevenlabs.py`): Lower latency, simpler code
- MCP Integration (`tts_elevenlabs_mcp.py`): Standardized, ecosystem compatible

Both options are available - choose based on your needs!

---

## Architecture

### Dual-Whisper STT (Unchanged)

Freya's speech-to-text architecture remains unchanged:

```
┌─────────────────────────────────────┐
│ Wake Word Detection                 │
│ Whisper TINY (always running)       │
│ ~1GB VRAM, ~50-100ms latency        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│ Full Speech Recognition             │
│ Whisper BASE (on-demand)            │
│ ~2GB VRAM, better accuracy          │
└─────────────────────────────────────┘
```

### TTS Engine Options (New)

Three TTS engines are now available:

```
┌────────────────────────────────────────────────────┐
│ TTS Engine Selection                               │
├────────────────────────────────────────────────────┤
│ 1. Piper (Local)                                   │
│    - Free, offline, fast                           │
│    - Basic quality                                 │
│    - Implementation: freya/voice/tts.py            │
├────────────────────────────────────────────────────┤
│ 2. ElevenLabs Direct API (Cloud)                   │
│    - Premium quality, low latency                  │
│    - Direct API calls                              │
│    - Implementation: freya/voice/tts_elevenlabs.py │
├────────────────────────────────────────────────────┤
│ 3. ElevenLabs MCP (Cloud) ← NEW!                   │
│    - Premium quality, MCP protocol                 │
│    - Standardized interface                        │
│    - Implementation: freya/voice/tts_elevenlabs_mcp.py │
└────────────────────────────────────────────────────┘
```

---

## Installation

### 1. Install ElevenLabs MCP Package

```bash
cd /path/to/freya_project
source venv/bin/activate
pip install elevenlabs-mcp==0.9.0
```

### 2. Set Environment Variables

Create or update `.env` file:

```bash
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=AXdMgz6evoL7OPd7eU12  # Your custom voice
```

### 3. Update Configuration

Edit `config/default.yaml`:

```yaml
tts:
  engine: "elevenlabs_mcp"  # Options: "piper", "elevenlabs", "elevenlabs_mcp"
  
  # ElevenLabs settings (used by both elevenlabs and elevenlabs_mcp)
  elevenlabs:
    api_key: ""  # Leave empty - set ELEVENLABS_API_KEY in .env
    voice_id: "AXdMgz6evoL7OPd7eU12"
    model: "eleven_turbo_v2_5"  # Fast model
    stability: 0.5
    similarity_boost: 0.75
    style: 0.0
    use_speaker_boost: true
```

---

## Files Added/Modified

### New Files

1. **`freya/voice/tts_elevenlabs_mcp.py`** (New)
   - ElevenLabs MCP TTS implementation
   - Wraps MCP server communication
   - Compatible with existing TTS interface

2. **`test_elevenlabs_mcp.py`** (New)
   - Test script for MCP TTS
   - Requires audio hardware

3. **`test_mcp_simple.py`** (New)
   - Simple MCP communication test
   - No audio hardware required

4. **`docs/ELEVENLABS_MCP_INTEGRATION.md`** (New)
   - This documentation file

### Modified Files

1. **`freya/agents/speech_agent.py`**
   - Added `ELEVENLABS_MCP` to `TTSEngine` enum
   - Added MCP TTS initialization in `_initialize_tts()`
   - No breaking changes to existing code

2. **`.env`** (Created if not exists)
   - Added `ELEVENLABS_API_KEY`
   - Added `ELEVENLABS_VOICE_ID`

---

## Usage

### Switching TTS Engines

#### Option 1: Configuration File

Edit `config/default.yaml`:

```yaml
tts:
  engine: "elevenlabs_mcp"  # Change this line
```

#### Option 2: Runtime (Future Enhancement)

```python
# Via message bus
await message_bus.publish(Message(
    topic="speech.change_engine",
    payload={"engine": "elevenlabs_mcp"},
))
```

### Testing

#### Test 1: Simple MCP Communication

```bash
python test_mcp_simple.py
```

This tests MCP server initialization without requiring audio hardware.

#### Test 2: Full TTS with Audio

```bash
python test_elevenlabs_mcp.py
```

This tests complete TTS pipeline including audio playback. **Requires:**
- Audio output device
- PortAudio library (`sudo apt-get install portaudio19-dev`)

#### Test 3: Integration Test

```bash
python main.py --mode text
```

Then type a message and Freya will respond using the configured TTS engine.

---

## Implementation Details

### MCP Communication Flow

```
┌──────────────────────────────────────────────────────┐
│ 1. SpeechAgent calls tts.speak(text)                 │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│ 2. ElevenLabsMCPTTS prepares MCP request             │
│    - Tool: "text_to_speech"                          │
│    - Args: {text, voice_id, model_id, ...}           │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│ 3. Spawn MCP server subprocess                       │
│    - python elevenlabs_mcp/server.py                 │
│    - Env: ELEVENLABS_API_KEY, OUTPUT_MODE=resources  │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│ 4. MCP server calls ElevenLabs API                   │
│    - Converts text to speech                         │
│    - Returns base64-encoded MP3 audio                │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│ 5. ElevenLabsMCPTTS decodes audio                    │
│    - Base64 decode → MP3 bytes                       │
│    - MP3 decode → PCM audio (pydub)                  │
└──────────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────┐
│ 6. Play audio via PyAudio                            │
│    - Stream PCM chunks to audio device               │
│    - Support stop signal (Ctrl+M)                    │
└──────────────────────────────────────────────────────┘
```

### Key Design Decisions

**1. Subprocess Communication**
- MCP servers use stdio protocol
- Each TTS call spawns a subprocess
- Overhead: ~100-200ms per call
- Trade-off: Standardization vs performance

**2. Output Mode: Resources**
- Set `ELEVENLABS_MCP_OUTPUT_MODE=resources`
- Audio returned as base64 in MCP response
- Alternative: `files` mode saves to disk (slower)

**3. Interface Compatibility**
- Same interface as `ElevenLabsTTS` and `TextToSpeech`
- Methods: `speak()`, `stop_speaking()`, `preload_phrase()`
- Drop-in replacement in `SpeechAgent`

**4. Error Handling**
- MCP errors propagated as `TextToSpeechError`
- Subprocess failures caught and logged
- Graceful fallback to other engines possible

---

## Performance Comparison

| Engine | Latency | Quality | Cost | Offline | MCP |
|--------|---------|---------|------|---------|-----|
| **Piper** | ~100ms | ⭐⭐⭐ | Free | ✅ | ❌ |
| **ElevenLabs API** | ~300ms | ⭐⭐⭐⭐⭐ | Paid | ❌ | ❌ |
| **ElevenLabs MCP** | ~500ms | ⭐⭐⭐⭐⭐ | Paid | ❌ | ✅ |

**Latency Breakdown (ElevenLabs MCP):**
- Subprocess spawn: ~50-100ms
- MCP protocol overhead: ~50ms
- ElevenLabs API call: ~200-300ms
- Audio decode + playback: ~100ms
- **Total:** ~500ms

**Recommendation:**
- **Real-time conversation:** Use `elevenlabs` (direct API)
- **MCP ecosystem integration:** Use `elevenlabs_mcp`
- **Offline/free:** Use `piper`

---

## Troubleshooting

### Issue: "ElevenLabs MCP server not found"

**Solution:**
```bash
pip install elevenlabs-mcp==0.9.0
```

### Issue: "ELEVENLABS_API_KEY environment variable is required"

**Solution:**
1. Create `.env` file in project root
2. Add: `ELEVENLABS_API_KEY=your_key_here`
3. Restart Freya

### Issue: "PortAudio library not found"

**Solution (Ubuntu/Debian):**
```bash
sudo apt-get install portaudio19-dev libportaudio2
```

**Solution (macOS):**
```bash
brew install portaudio
```

### Issue: "No audio output"

**Possible causes:**
1. Running in headless environment (no audio device)
2. Audio device permissions
3. Wrong audio device selected

**Debug:**
```python
import sounddevice as sd
print(sd.query_devices())  # List available audio devices
```

### Issue: "MCP server timeout"

**Possible causes:**
1. Network connectivity (ElevenLabs API unreachable)
2. API quota exceeded
3. Invalid API key

**Debug:**
- Check internet connection
- Verify API key in ElevenLabs dashboard
- Check API usage/quota

---

## Future Enhancements

### Phase 2: GUI Configuration

Add GUI panel for TTS engine selection:

```
┌─────────────────────────────────────────┐
│ Text-to-Speech Engine                   │
├─────────────────────────────────────────┤
│ ○ Piper (Local, Free)        ⭐⭐⭐     │
│ ○ ElevenLabs API (Cloud)     ⭐⭐⭐⭐⭐   │
│ ● ElevenLabs MCP (Cloud)     ⭐⭐⭐⭐⭐   │
│                                         │
│ Voice: [AXdMgz6evoL7OPd7eU12 ▼]         │
│ Model: [eleven_turbo_v2_5    ▼]         │
│                                         │
│                    [Apply]  [Test]      │
└─────────────────────────────────────────┘
```

### Phase 3: Additional MCP Servers

Integrate more MCP servers:
- **Fast-Whisper MCP:** Alternative STT (local)
- **Brave Search MCP:** Web search
- **Git MCP:** Version control operations
- **Memory MCP:** Enhanced knowledge graph

### Phase 4: MCP Server Manager

Central MCP server management:
- List available MCP servers
- Install/uninstall MCP packages
- Configure server settings
- Monitor server health

---

## API Reference

### ElevenLabsMCPTTS

```python
class ElevenLabsMCPTTS:
    """Convert text to speech using ElevenLabs MCP server."""
    
    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_turbo_v2_5",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        speed: float = 1.0,
    ) -> None:
        """Initialize ElevenLabs MCP TTS.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use
            model_id: Model to use (turbo_v2_5 for speed)
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity (0-1)
            style: Style exaggeration (0-1)
            use_speaker_boost: Enable speaker boost
            speed: Speech speed (0.7-1.2)
        """
    
    def speak(self, text: str) -> None:
        """Synthesize and play text.
        
        Args:
            text: Text to convert to speech
            
        Raises:
            TextToSpeechError: If synthesis or playback fails
        """
    
    def stop_speaking(self) -> None:
        """Stop current playback."""
    
    def preload_phrase(self, text: str) -> None:
        """Preload phrase (no-op for MCP)."""
```

---

## Dependencies

### Python Packages

```
elevenlabs-mcp==0.9.0
mcp>=1.12.4
pydub
pyaudio
python-dotenv
```

### System Libraries

```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev libportaudio2 ffmpeg

# macOS
brew install portaudio ffmpeg
```

---

## Contributing

### Adding New MCP Servers

1. Install MCP package: `pip install <mcp-package>`
2. Create wrapper in `freya/voice/` or `freya/tools/`
3. Add to `SpeechAgent` or appropriate coordinator
4. Update configuration schema
5. Add tests
6. Document in `docs/`

### Testing Checklist

- [ ] MCP server communication works
- [ ] Audio synthesis succeeds
- [ ] Audio playback works
- [ ] Stop signal works (Ctrl+M)
- [ ] Error handling works
- [ ] Configuration loading works
- [ ] Engine switching works
- [ ] Integration with SpeechAgent works

---

## License

Same as Freya project.

---

## Support

For issues:
1. Check troubleshooting section
2. Review logs in `logs/freya.log`
3. Test with `test_mcp_simple.py`
4. Open GitHub issue with logs

---

**Built with ❤️ for the MCP ecosystem**
