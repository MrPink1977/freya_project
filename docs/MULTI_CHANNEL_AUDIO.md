# Multi-Channel Audio System

## Overview

Freya now supports **multi-channel audio** with intelligent routing and channel isolation. This enables seamless interaction through multiple audio sources:

- **PC**: Default microphone and speakers
- **Doorbell** (Reolink camera): RTSP audio stream (future)
- **Additional channels**: Easily extensible

## Architecture

### Components

1. **SpeechAgent** (`freya/agents/speech_agent.py`)
   - Coordinates all STT/TTS operations
   - Multi-channel audio routing
   - Dynamic TTS engine switching (Piper ↔ ElevenLabs)
   - Channel-aware audio processing

2. **AudioChannelManager** (`freya/coordination/audio_channel_manager.py`)
   - Smart channel prioritization
   - Automatic channel muting/unmuting
   - Conflict resolution (multiple wake events)
   - Channel health monitoring

3. **Updated WakeWordAgent**
   - Now includes `channel_id` in wake detection
   - Each agent can listen on a specific channel

## Features

### Smart Channel Routing

```
Doorbell wake → PC mutes → Respond on doorbell → PC unmutes
PC wake while doorbell active → Queue or interrupt based on priority
```

### Channel Priority System

- **Doorbell**: Priority 10 (exclusive, cannot be interrupted)
- **PC**: Priority 1 (can be interrupted by higher priority)

### Channel States

- `IDLE`: Available for use
- `LISTENING`: Actively listening for speech
- `SPEAKING`: Playing TTS audio
- `MUTED`: Temporarily disabled (by channel manager)
- `DISABLED`: Permanently disabled (too many errors)

## Configuration

### config/default.yaml

```yaml
tts:
  engine: "elevenlabs"  # or "piper"
  
  # ElevenLabs settings
  elevenlabs:
    api_key: "your_api_key_here"
    voice_id: "AXdMgz6evoL7OPd7eU12"  # Your custom voice
    model: "eleven_turbo_v2_5"  # Fast model
```

## Usage

### Basic Voice Interaction

```bash
# Start with ElevenLabs
python main.py --engine elevenlabs

# Start with Piper (local)
python main.py --engine piper

# Text mode
python main.py --mode text
```

### Test TTS Quality

```bash
# Compare Piper vs ElevenLabs
python test_tts_comparison.py
```

This will speak the same phrase with both engines so you can decide which sounds better.

### Programmatic Channel Control

```python
# Register a new channel
await speech_agent.register_channel(
    channel_id="doorbell",
    name="Reolink Doorbell",
    stt_device=1,  # Specific audio device
    tts_device=1,
)

# Mute/unmute channels
await speech_agent.mute_channel("pc")
await speech_agent.unmute_channel("pc")

# Change TTS engine on-the-fly
await message_bus.publish(Message(
    topic="speech.change_engine",
    payload={"engine": "elevenlabs"},
))
```

## Event Flow

### Wake Detection → Response

```
1. WakeWordAgent detects "Hey, Freya" on channel_id="pc"
2. Publishes: wake.detected(channel_id="pc", transcript="...")
3. AudioChannelManager evaluates routing:
   - Checks priority, active channels, conflicts
   - Mutes other channels if needed
4. Publishes: channel.routing_decision(action="activated")
5. OrchestrationCoordinator queries memory
6. Sends to DialogAgent for LLM response
7. DialogAgent streams chunks to SpeechAgent
8. SpeechAgent speaks on correct channel
9. On completion: speech.speech_complete → channel released
```

## TTS Engine Comparison

### Piper (Local)
- ✅ **Pros**: Fast, offline, free, no API needed
- ❌ **Cons**: Robotic sound, limited voices

### ElevenLabs (Cloud)
- ✅ **Pros**: Natural voice, emotional range, custom voices
- ❌ **Cons**: Requires API key, internet, costs money

**Recommendation**: Test both with `test_tts_comparison.py` and decide!

## Future Enhancements

### Planned Features

1. **Reolink Doorbell Integration**
   - RTSP audio streaming
   - Two-way audio (listen + speak)
   - Automatic channel registration

2. **Vision Integration**
   - Facial recognition at door
   - Context-aware responses ("Hi Tommy!")
   - Object detection (YOLO)

3. **Smart Automations**
   - Motion detection → wake
   - Scheduled announcements
   - Multi-room audio routing

## Troubleshooting

### ElevenLabs Not Working

1. Check API key in `config/default.yaml`
2. Verify internet connection
3. Check ElevenLabs account quota
4. View logs: `logs/freya.log`

### Channel Conflicts

Check channel status programmatically:
```python
status = audio_channel_manager.get_channel_status()
print(status)
```

### Audio Device Issues

List available audio devices:
```python
import sounddevice as sd
print(sd.query_devices())
```

## Technical Details

### Message Topics

**SpeechAgent**:
- `speech.listen_request` → Start listening on channel
- `speech.speak_request` → Speak on channel
- `speech.transcription` → STT result
- `speech.speech_started` → TTS started
- `speech.speech_complete` → TTS finished
- `speech.change_engine` → Switch TTS engine
- `speech.mute_channel` → Mute channel
- `speech.unmute_channel` → Unmute channel

**AudioChannelManager**:
- `wake.detected` → Route to correct channel
- `channel.routing_decision` → Activation/rejection
- `channel.mute` → Manual mute
- `channel.unmute` → Manual unmute

### Architecture Benefits

1. **Decoupled**: Agents communicate via MessageBus
2. **Extensible**: Add new channels without changing core code
3. **Testable**: Each component independently testable
4. **Scalable**: Can handle many concurrent channels
5. **Resilient**: Failed channels auto-disable, others continue

## API Reference

### SpeechAgent Methods

```python
await speech_agent.register_channel(channel_id, name, stt_device, tts_device)
await speech_agent.mute_channel(channel_id)
await speech_agent.unmute_channel(channel_id)
active = speech_agent.get_active_channel()
```

### AudioChannelManager Methods

```python
await channel_manager.register_channel(channel_id, rule)
status = channel_manager.get_channel_status()
```

---

**Built with** ❤️ **for voice-first AI interaction**
