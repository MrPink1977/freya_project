# Multi-Channel Audio Integration Notes

This document outlines how Freya's current architecture could be extended to
support an additional Reolink IP camera audio channel alongside the existing
primary microphone/speaker pipeline.

## Architectural fit

Freya already separates responsibilities across the orchestrator, STT/TTS
services, wake detection, and memory subsystems. A multi-channel manager can
hook in ahead of the orchestrator to arbitrate which channel owns the active
conversation while the orchestrator itself remains unchanged.

```
+----------------+        +------------------+        +-----------------+
| Wake Detector  | ---->  | Multi-Channel    | ---->  | Orchestrator    |
| (per channel)  |        | Coordinator      |        | (existing loop) |
+----------------+        +------------------+        +-----------------+
```

* Each channel runs a lightweight wake-word detector (e.g., faster-whisper
tiny) that emits transcripts every 2 seconds.
* The coordinator keeps a `conversation_lock` and `active_channel` identifier.
* When the first channel detects the wake phrase, it acquires the lock and
  forwards audio to the orchestrator for the full STT → Ollama → TTS cycle.
* The other channel keeps listening but ignores triggers until the lock is
  released.

## Implementation effort

| Area                         | Notes                                                                           |
|------------------------------|---------------------------------------------------------------------------------|
| Audio capture/playback       | Reolink audio arrives via RTSP; use `opencv-python` or `ffmpeg` to demux audio. |
| Wake detection loop          | Reuse `WakeWordDetector` with channel-specific audio sources.                   |
| Conversation arbitration     | Light threading work similar to the provided `MultiChannelAudioManager`.        |
| TTS routing                  | Piper already streams PCM chunks; write channel-specific speakers.              |
| Testing/observability        | Add diagnostics to ensure lock hand-off behaves as expected.                   |

With the existing modular design, adding the coordinator layer is moderate in
complexity (roughly a few days of work to polish). The heaviest lift is the
camera-specific audio extraction, because Reolink’s RTSP stream multiplexes
video and audio. Once PCM data is available, the rest slots into the current
STT/TTS pipeline.

## Key considerations

1. **Thread safety** – keep the orchestrator single-threaded by funneling all
   channel events through the coordinator.
2. **Resource usage** – running wake detectors per channel typically consumes
   10–15% CPU on current hardware, but budget for higher usage on slower
   machines and consider mixing detector models (e.g., a heavier local mic
   model and a lighter camera-specific one) to stay responsive.
3. **Latency** – expect the Reolink RTSP path to introduce an extra
   ~200–500 ms; compensate by slightly lengthening the wake buffer or
   staggering the coordinator’s checks so late triggers do not pre-empt a live
   conversation.
4. **Fallback behaviour** – if the camera drops offline, mark the channel as
   disabled and fall back to the primary microphone automatically.
5. **Configuration** – extend `config/default.yaml` with channel definitions so
   new hardware can be enabled without code changes.
6. **Testing** – provide a simulated audio source for unit tests to avoid
   hardware dependencies.
7. **Vision hooks** – feeds that supply video frames can reuse
   `freya.facial_recognition` to identify known visitors without altering the
   audio pipeline.

### RTSP audio extraction

The main engineering effort is demuxing the camera’s RTSP stream into PCM
audio. A practical approach is to lean on `ffmpeg` and pipe the decoded audio
directly to the wake detector:

```
ffmpeg -rtsp_transport tcp \
       -i rtsp://user:pass@IP:554/h264Preview_01_main \
       -vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le pipe:1
```

The coordinator can read from the pipe in small windows (e.g., 1 s) and feed
them into the existing detection loop. This avoids reimplementing AAC decoding
and works reliably with Reolink hardware.

For backchannel audio, many Reolink models expose an ONVIF “speaker” service.
Expect to issue `StartTwoWayAudio` requests and stream PCM chunks; some models
require specific firmware settings or HTTPS, so keep a diagnostic script handy.

### Example configuration

```
audio:
  channels:
    primary:
      type: system
      enabled: true
    camera_front_door:
      type: reolink
      ip: 192.168.1.100
      rtsp_port: 554
      username: ${CAMERA_USER}
      password: ${CAMERA_PASS}
      enabled: true
```

This layout lets each channel declare its source and credentials while keeping
the orchestrator unaware of the underlying hardware.

Overall, implementing a Reolink IP camera channel is feasible and leverages
Freya’s current separation of concerns. The project primarily requires
plumbing new audio sources into the wake detection loop and ensuring exclusive
conversation ownership during a session.