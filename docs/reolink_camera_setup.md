# Reolink Camera Integration Guide

This guide explains how to set up and use Reolink IP cameras as additional audio input sources for Freya, enabling multi-room voice assistance with two-way audio.

## Features

- **Multi-Channel Audio**: Support for multiple audio input sources (system mic + multiple cameras)
- **Two-Way Audio**: Speak through camera speakers using Freya's TTS
- **Wake Word Detection**: Each camera listens for the wake word independently
- **Conversation Arbitration**: First channel to detect wake word gets control
- **Facial Recognition**: Optional video processing for recognizing known faces
- **Auto-Reconnection**: Automatic reconnection if camera stream drops

## Architecture

```
┌─────────────────┐        ┌──────────────────┐        ┌─────────────────┐
│ Wake Detector   │ ────>  │ Multi-Channel    │ ────>  │ Orchestrator    │
│ (per channel)   │        │ Coordinator      │        │ (existing loop) │
└─────────────────┘        └──────────────────┘        └─────────────────┘
```

Each channel (system mic or camera) runs its own wake word detector. The coordinator manages which channel owns the active conversation and routes audio/TTS accordingly.

## Prerequisites

### 1. Install Required Dependencies

```bash
pip install opencv-python>=4.8.0 onvif-zeep>=0.2.12
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Install ffmpeg

The RTSP stream handler requires ffmpeg for audio extraction:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH.

### 3. Configure Your Reolink Cameras

Ensure your Reolink cameras have:
- Fixed IP addresses (set via router DHCP reservation or camera static IP)
- RTSP enabled (usually enabled by default)
- Known username and password
- Network accessibility from the machine running Freya

**Finding RTSP URL:**
Most Reolink cameras use: `rtsp://username:password@IP:554/h264Preview_01_main`

**Testing Connection:**
```bash
ffmpeg -rtsp_transport tcp -i rtsp://admin:password@192.168.1.100:554/h264Preview_01_main -t 5 test.mp4
```

## Configuration

### Step 1: Create Audio Channel Configuration

Create a configuration file (or modify `config/default.yaml`) with your camera details:

```yaml
audio:
  channels:
    # Primary system microphone
    primary:
      type: system
      enabled: true
      device_index: null
      description: "Desktop microphone"

    # First Reolink camera
    camera_front_door:
      type: reolink
      enabled: true
      ip: "192.168.1.100"
      rtsp_port: 554
      username: "${REOLINK_FRONT_USER}"
      password: "${REOLINK_FRONT_PASS}"
      description: "Front door camera"

    # Second Reolink camera
    camera_garage:
      type: reolink
      enabled: true
      ip: "192.168.1.101"
      rtsp_port: 554
      username: "${REOLINK_GARAGE_USER}"
      password: "${REOLINK_GARAGE_PASS}"
      description: "Garage camera"
```

### Step 2: Set Environment Variables

For security, use environment variables for credentials:

**Linux/macOS:**
```bash
export REOLINK_FRONT_USER="admin"
export REOLINK_FRONT_PASS="your_password_here"
export REOLINK_GARAGE_USER="admin"
export REOLINK_GARAGE_PASS="your_password_here"
```

**Windows (PowerShell):**
```powershell
$env:REOLINK_FRONT_USER="admin"
$env:REOLINK_FRONT_PASS="your_password_here"
$env:REOLINK_GARAGE_USER="admin"
$env:REOLINK_GARAGE_PASS="your_password_here"
```

Or create a `.env` file (add to `.gitignore`):
```
REOLINK_FRONT_USER=admin
REOLINK_FRONT_PASS=your_password_here
REOLINK_GARAGE_USER=admin
REOLINK_GARAGE_PASS=your_password_here
```

### Step 3: Optional - Enable Facial Recognition

If you want cameras to recognize faces:

```yaml
vision:
  facial_recognition:
    enabled: true
    camera_channel: "camera_front_door"  # Which camera to process
    known_faces_dir: "data/faces"
    detection_model: "hog"  # Fast but less accurate
    # detection_model: "cnn"  # Slower but more accurate
    encoding_model: "small"
    tolerance: 0.5
    min_recognition_interval: 5.0
```

Create face profiles by adding images to `data/faces/`:
```
data/faces/
  john/
    john1.jpg
    john2.jpg
  sarah/
    sarah1.jpg
```

## Usage

### Basic Multi-Channel Operation

When running Freya with multi-channel configuration:

1. **All channels listen simultaneously** for the wake word
2. **First to detect** wake word acquires conversation lock
3. **Audio routing**:
   - If wake word detected on system mic → listen via system mic, speak via system speakers
   - If wake word detected on camera → listen via camera, speak via camera speaker
4. **Other channels** continue listening but ignore wake words during active conversation
5. **Conversation ends** when timeout expires or user says "exit"

### Example Session

**Scenario: User speaks to front door camera**

```
[All channels listening...]

Camera Front Door: *detects "Hey Freya"*
[Front door camera acquires lock]

User (at front door): "Hey Freya, what's the weather?"
Freya (via front door speaker): "It's currently 72 degrees and sunny..."

[Conversation timeout - lock released]
[All channels listening again...]
```

**Scenario: User speaks to system microphone**

```
[All channels listening...]

System Primary: *detects "Hey Freya"*
[System mic acquires lock]

User (at desk): "Hey Freya, set a reminder"
Freya (via desktop speakers): "What would you like to be reminded about?"

[Conversation continues via desktop until timeout]
```

## Code Integration Example

### Using the Multi-Channel Coordinator

```python
from freya.audio_config import load_channel_configs
from freya.coordinator import MultiChannelCoordinator, WakeEvent, AudioEvent

# Load channel configurations
channels = load_channel_configs("config/default.yaml")

# Define callbacks
def on_wake(event: WakeEvent):
    print(f"Wake word detected on {event.channel_id}: {event.transcript}")
    # Start conversation on this channel

def on_audio(event: AudioEvent):
    print(f"Audio from {event.channel_id}: {len(event.audio_data)} bytes")
    # Process audio for STT

# Create and start coordinator
coordinator = MultiChannelCoordinator(
    channels,
    wake_callback=on_wake,
    audio_callback=on_audio,
    conversation_timeout=30.0
)

coordinator.start()

# Run your main loop...
# coordinator will handle channel arbitration

coordinator.stop()
```

### Using RTSP Stream Handler Directly

```python
from freya.rtsp_stream import RTSPStreamHandler, AudioChunk, VideoFrame
from freya.multi_channel_coordinator import ChannelConfig, ChannelType

# Create channel config
config = ChannelConfig(
    channel_id="my_camera",
    channel_type=ChannelType.REOLINK,
    ip="192.168.1.100",
    rtsp_port=554,
    username="admin",
    password="password"
)

# Define callbacks
def on_audio(chunk: AudioChunk):
    # Process 16kHz mono PCM audio
    print(f"Audio: {len(chunk.data)} bytes at {chunk.sample_rate}Hz")

def on_video(frame: VideoFrame):
    # Process BGR video frame
    print(f"Frame: {frame.frame.shape} at {frame.timestamp}")

# Start streaming
with RTSPStreamHandler(config, audio_callback=on_audio, video_callback=on_video) as stream:
    # Stream runs in background threads
    time.sleep(60)  # Stream for 60 seconds
```

### Using ONVIF Two-Way Audio

```python
from freya.onvif_client import ONVIFAudioClient, CameraTTSOutput

# Create ONVIF client
client = ONVIFAudioClient(config, sample_rate=8000)

# Start session
if client.start_session():
    # Stream TTS audio to camera speaker
    tts_output = CameraTTSOutput(client)

    # Get audio from your TTS engine
    audio_chunks = tts.synthesize("Hello from Freya!")
    tts_output.play_chunks(audio_chunks)

    client.stop_session()
```

## Troubleshooting

### Camera Connection Issues

**Problem**: "Failed to start channel" errors

**Solutions**:
1. Verify camera IP address: `ping 192.168.1.100`
2. Test RTSP connection: `ffmpeg -i rtsp://user:pass@IP:554/h264Preview_01_main -t 2 test.mp4`
3. Check credentials are correct
4. Ensure RTSP is enabled on camera (usually in Settings > Network > Advanced)
5. Try different RTSP URLs:
   - Main stream: `/h264Preview_01_main`
   - Sub stream: `/h264Preview_01_sub`

### Audio Quality Issues

**Problem**: Choppy or garbled audio from camera

**Solutions**:
1. Use sub-stream instead of main stream for better performance
2. Check network bandwidth (cameras can use 2-8 Mbps)
3. Reduce number of simultaneous video streams
4. Position camera closer to WiFi access point (if using WiFi)

### Wake Word Not Detected on Camera

**Problem**: Camera channel never detects wake word

**Solutions**:
1. Check audio extraction is working (check logs for "Audio extraction started")
2. Test camera microphone quality (record RTSP stream and listen)
3. Adjust wake word detector sensitivity in configuration
4. Ensure camera is in range to hear wake word clearly
5. Some cameras have poor built-in mics - consider external mic via camera's audio input

### Two-Way Audio Not Working

**Problem**: Cannot hear Freya through camera speaker

**Solutions**:
1. Verify camera supports two-way audio (check camera specs)
2. Enable two-way audio in camera settings
3. Some Reolink models require specific firmware versions
4. Try using Reolink's HTTP API instead of ONVIF (implementation varies by model)
5. Check camera speaker volume settings

### High CPU Usage

**Problem**: High CPU usage with multiple cameras

**Solutions**:
1. Disable video processing if not using facial recognition
2. Use "hog" detection model instead of "cnn" for face recognition
3. Limit frame rate in rtsp_stream.py (default is ~5fps for efficiency)
4. Use camera sub-streams instead of main streams
5. Disable unused channels in configuration

## Performance Considerations

- **Each camera channel** adds ~10-15% CPU for wake detection + audio extraction
- **Video processing** (facial recognition) adds ~20-30% CPU per camera
- **Recommended maximum**: 3-4 active camera channels on typical hardware
- **Network bandwidth**: Each camera main stream uses 2-8 Mbps, sub-stream uses 0.5-2 Mbps

## Security Best Practices

1. **Use strong passwords** for camera accounts
2. **Create dedicated camera user** with limited permissions (not admin)
3. **Store credentials in environment variables**, not in config files
4. **Isolate cameras** on separate VLAN if possible
5. **Update camera firmware** regularly for security patches
6. **Use HTTPS/TLS** for camera connections when available
7. **Add config files with credentials to .gitignore**

## Advanced Configuration

### Custom Wake Word Per Channel

You can configure different wake words for different channels (future enhancement):

```yaml
audio:
  channels:
    primary:
      type: system
      wake_word: "hey freya"

    camera_bedroom:
      type: reolink
      wake_word: "bedroom assistant"
```

### Priority Channels

Configure channel priority for conflict resolution (future enhancement):

```yaml
audio:
  channels:
    primary:
      type: system
      priority: 100  # Highest priority

    camera_front:
      type: reolink
      priority: 50
```

## Known Limitations

1. **ONVIF Two-Way Audio**: Implementation varies by camera model. Some Reolink models may require proprietary API instead of ONVIF.
2. **Latency**: Camera audio has ~200-500ms latency compared to system microphone
3. **Simultaneous Speakers**: Only one channel can be active at a time (by design)
4. **Stream Reconnection**: 3-second delay when reconnecting after stream drop
5. **Face Recognition**: Only one camera can be used for face recognition at a time

## Future Enhancements

- [ ] Reolink proprietary API support for better two-way audio compatibility
- [ ] Multi-camera facial recognition (parallel processing)
- [ ] Custom wake words per channel
- [ ] Channel priority configuration
- [ ] Motion detection integration
- [ ] Recording and replay capabilities
- [ ] Web UI for camera status and configuration

## Support

For issues or questions:
- Check logs in the console for detailed error messages
- Review Reolink camera documentation for model-specific features
- Test RTSP connection independently with ffmpeg before reporting issues
- Provide camera model and firmware version when reporting bugs

## References

- [Reolink RTSP Guide](https://support.reolink.com/hc/en-us/articles/360007010473-How-to-Live-View-Reolink-Cameras-via-VLC-Media-Player)
- [ONVIF Specification](https://www.onvif.org/specs/stream/ONVIF-Streaming-Spec.pdf)
- [FFmpeg RTSP Documentation](https://ffmpeg.org/ffmpeg-protocols.html#rtsp)
