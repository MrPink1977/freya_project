# Freya Home Assistant Integration

This document describes the complete Home Assistant setup for the Freya voice assistant project, including Docker configuration, Voice PE hardware integration, and custom wake word training.

## Overview

The Freya project integrates with Home Assistant to provide a complete voice assistant ecosystem combining:

- **Home Assistant Core**: Central hub for automation and device management
- **Wyoming Protocol Services**: Speech-to-text (Whisper), text-to-speech (Piper), and wake word detection (OpenWakeWord)
- **Ollama**: Local LLM inference for conversational AI
- **ChromaDB**: Vector database for semantic memory
- **Voice PE Device**: ESP32-based hardware for always-listening wake word detection
- **Home Agent Integration**: Connects Ollama LLMs to Home Assistant for natural language control

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Windows Host System                          │
│  Location: C:\AI_Projects\homeassistant\                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Containers                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Home Assistant   │  │ Wyoming-Whisper  │  │ Wyoming-Piper │ │
│  │ Port: 8123       │  │ Port: 10300      │  │ Port: 10200   │ │
│  │                  │  │ (Speech-to-Text) │  │ (Text-to-     │ │
│  │ • ESPHome        │  │                  │  │  Speech)      │ │
│  │ • Home Agent     │  │ Model: base      │  │               │ │
│  │ • Automations    │  │                  │  │ Voice: en_US  │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│           │                     │                     │          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ OpenWakeWord     │  │ Ollama           │  │ ChromaDB      │ │
│  │ Port: 10400      │  │ Port: 11434      │  │ Port: 8000    │ │
│  │                  │  │                  │  │               │ │
│  │ Wake words:      │  │ Models:          │  │ Vector store  │ │
│  │ • Hey Jarvis     │  │ • llama3.2:3b    │  │ for semantic  │ │
│  │ • Hey Mycroft    │  │ • dolphin-mixtral│  │ memory        │ │
│  │ • (Custom)       │  │ • deepseek-coder │  │               │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Voice PE Device (ESP32)                       │
│  IP: 192.168.0.52                                                │
│                                                                   │
│  • Always-listening microphone                                   │
│  • On-device wake word detection (microWakeWord)                │
│  • LED ring feedback                                             │
│  • Connects to Home Assistant via ESPHome                        │
│  • Streams audio to Wyoming-Whisper when wake word detected      │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
C:\AI_Projects\homeassistant\
├── config/                          # Home Assistant configuration
│   ├── configuration.yaml           # Main HA config
│   ├── automations.yaml            # Automation rules
│   ├── custom_components/          # Custom integrations
│   │   └── home_agent/             # Home Agent integration
│   ├── esphome/                    # ESPHome device configs
│   │   └── voice-pe-*.yaml         # Voice PE configuration
│   └── custom_wakewords/           # Custom wake word models
│       ├── hey_freya.tflite        # Trained model
│       └── hey_freya.json          # Model manifest
├── docker-compose.yml              # Container orchestration
├── microwakeword_training/         # Wake word training workspace
│   ├── generated_samples/          # Synthetic voice samples
│   ├── personal_samples/           # User voice recordings
│   └── my_custom_model/            # Trained model output
└── .wslconfig                      # WSL2 resource limits
```

## Installation & Setup

### Prerequisites

- **Windows 10/11** with WSL2 enabled
- **Docker Desktop** installed and running
- **16GB+ RAM** (12GB allocated to WSL2 for training)
- **Home Assistant Voice PE** device (or compatible ESP32 hardware)
- **Network connectivity** between all components

### Step 1: WSL2 Configuration

Create or edit `C:\Users\<username>\.wslconfig`:

```ini
[wsl2]
memory=12GB
processors=6
swap=4GB
```

Restart WSL2:
```powershell
wsl --shutdown
```

### Step 2: Docker Compose Setup

Create `docker-compose.yml` in `C:\AI_Projects\homeassistant\`:

```yaml
version: '3.8'

services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
    network_mode: host

  wyoming-whisper:
    container_name: wyoming-whisper
    image: rhasspy/wyoming-whisper:latest
    volumes:
      - ./whisper_data:/data
    ports:
      - "10300:10300"
    command: --model base --language en
    restart: unless-stopped

  wyoming-piper:
    container_name: wyoming-piper
    image: rhasspy/wyoming-piper:latest
    volumes:
      - ./piper_data:/data
    ports:
      - "10200:10200"
    command: --voice en_US-lessac-medium
    restart: unless-stopped

  wyoming-openwakeword:
    container_name: wyoming-openwakeword
    image: rhasspy/wyoming-openwakeword:latest
    volumes:
      - ./openwakeword_data:/data
      - ./config/custom_wakewords:/custom
    ports:
      - "10400:10400"
    command: --preload-model hey_jarvis --custom-model-dir /custom
    restart: unless-stopped

  ollama:
    container_name: ollama
    image: ollama/ollama:latest
    volumes:
      - ./ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  chromadb:
    container_name: chromadb
    image: chromadb/chroma:latest
    volumes:
      - ./chroma_data:/chroma/chroma
    ports:
      - "8000:8000"
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    restart: unless-stopped
```

### Step 3: Start Services

```powershell
cd C:\AI_Projects\homeassistant
docker-compose up -d
```

Verify all containers are running:
```powershell
docker ps
```

### Step 4: Install Ollama Models

```powershell
docker exec -it ollama ollama pull llama3.2:3b
docker exec -it ollama ollama pull dolphin-mixtral:8x7b
docker exec -it ollama ollama pull deepseek-coder-v2:16b-lite
```

### Step 5: Configure Home Assistant

1. Open Home Assistant: `http://192.168.0.50:8123`
2. Complete initial setup wizard
3. Install **Home Agent** integration:
   - Settings → Devices & Services → Add Integration
   - Search for "Home Agent"
   - Configure Ollama host: `http://192.168.0.50:11434`
   - Select model: `llama3.2:3b`

4. Add Wyoming Protocol integrations:
   - **Wyoming Protocol** (Whisper): `http://192.168.0.50:10300`
   - **Wyoming Protocol** (Piper): `http://192.168.0.50:10200`
   - **Wyoming Protocol** (OpenWakeWord): `http://192.168.0.50:10400`

5. Configure Voice Assistant:
   - Settings → Voice assistants → Add assistant
   - Name: "Freya"
   - Conversation agent: Home Agent
   - Speech-to-text: Wyoming (Whisper)
   - Text-to-speech: Wyoming (Piper)
   - Wake word: Hey Jarvis (or custom)

### Step 6: Voice PE Device Setup

#### Option A: Adopt Existing Voice PE

1. Go to Settings → Devices & Services → ESPHome
2. Find your Voice PE device (e.g., `home-assistant-voice-0a52fa`)
3. Click "Adopt" to take control
4. Device will appear in ESPHome dashboard

#### Option B: Flash New ESP32 Device

1. Install ESPHome dashboard add-on in Home Assistant
2. Create new device configuration
3. Use Voice PE template from ESPHome GitHub
4. Flash via USB or OTA

### Step 7: Configure Voice PE for Custom Wake Word

Edit the ESPHome configuration for your Voice PE:

```yaml
substitutions:
  name: home-assistant-voice-0a52fa
  friendly_name: Home Assistant Voice 0a52fa

packages:
  Nabu Casa.Home Assistant Voice PE: github://esphome/voice-kit/home-assistant-voice.yaml

esphome:
  name: ${name}
  name_add_mac_suffix: false
  friendly_name: ${friendly_name}

api:
  encryption:
    key: !secret api_key

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

# Add custom wake word
micro_wake_word:
  models:
    - model: /config/custom_wakewords/hey_freya.json
      id: hey_freya
    # Optionally remove default models to save memory
    - id: !remove hey_mycroft
```

Install updated configuration to Voice PE device.

## Custom Wake Word Training

### Overview

The Voice PE device uses **microWakeWord** for on-device wake word detection. To train a custom wake word like "Hey Freya", we use a Docker-based training environment.

### Training Process

#### Step 1: Setup Training Environment

```powershell
cd C:\AI_Projects\homeassistant
mkdir microwakeword_training
cd microwakeword_training
```

#### Step 2: Pull Training Container

```powershell
docker pull ghcr.io/tatertotterson/microwakeword:latest
```

#### Step 3: (Optional) Record Personal Voice Samples

For better accuracy, record yourself saying "Hey Freya" 10-30 times:

```powershell
mkdir personal_samples
# Use Windows Voice Recorder or phone to record
# Save as .wav files: hey_freya_01.wav, hey_freya_02.wav, etc.
# Copy to personal_samples/ folder
```

**Recording Tips:**
- Vary distance (close, far)
- Vary volume (quiet, normal, loud)
- Vary tone (casual, urgent)
- Record in the environment where you'll use it
- Use 16-bit WAV format if possible

#### Step 4: Start Training Container

```powershell
docker run --rm -it -p 8888:8888 -v ${PWD}:/data ghcr.io/tatertotterson/microwakeword:latest
```

For GPU acceleration (if available):
```powershell
docker run --rm -it --gpus all -p 8888:8888 -v ${PWD}:/data ghcr.io/tatertotterson/microwakeword:latest
```

#### Step 5: Configure Training Parameters

1. Open browser: `http://localhost:8888`
2. Open `microWakeWord_training_notebook.ipynb`
3. Edit parameters:
   ```python
   TARGET_WORD = "hey_freya"  # Your wake word
   MAX_SAMPLES = 10000        # Reduce from 50000 to avoid OOM
   BATCH_SIZE = 100           # Keep default
   ```

#### Step 6: Run Training

1. Click **Run** → **Run All Cells**
2. Wait for training to complete (1-4 hours depending on CPU/GPU)
3. Monitor progress in notebook output

#### Step 7: Extract Trained Model

After training completes, download files:
- `hey_freya.tflite` - The model file
- `hey_freya.json` - The manifest file

Copy to Home Assistant:
```powershell
copy my_custom_model\hey_freya.* C:\AI_Projects\homeassistant\config\custom_wakewords\
```

#### Step 8: Deploy to Voice PE

1. Update ESPHome configuration (see Step 7 above)
2. Click "Install" in ESPHome dashboard
3. Wait for compilation and OTA update
4. Device will reboot with new wake word

#### Step 9: Select Wake Word in Home Assistant

1. Settings → Voice assistants → Edit "Freya"
2. Wake word dropdown → Select "Hey Freya"
3. Save

### Troubleshooting Training Issues

**Out of Memory (OOM) Errors:**
- Reduce `MAX_SAMPLES` to 10000 or 5000
- Increase WSL2 memory allocation in `.wslconfig`
- Close other applications during training

**Training Freezes:**
- Check Docker Desktop logs
- Verify WSL2 has sufficient resources
- Try CPU-only training (remove `--gpus all`)

**Poor Wake Word Detection:**
- Retrain with personal voice samples
- Adjust `probability_cutoff` in JSON manifest (lower = more sensitive)
- Record more diverse samples (different distances, volumes)

**Model Won't Load on Voice PE:**
- Verify both `.tflite` and `.json` files are in `/config/custom_wakewords/`
- Check ESPHome logs for compilation errors
- Ensure model path in YAML is correct

## Integration with Freya Agent System

The Home Assistant setup provides the voice interface, while the Freya agent system (from the main repository) handles:

- **Advanced conversation**: Multi-turn dialog with context
- **Memory management**: ChromaDB vector storage for long-term memory
- **Tool execution**: Time, calculator, file operations, web search
- **Model escalation**: Smart switching between fast and reasoning models
- **Vision capabilities**: Facial recognition and camera integration

### Connecting Freya to Home Assistant

1. Configure Freya to use Home Assistant's Wyoming services:
   ```yaml
   # config/my_config.yaml
   audio:
     stt:
       engine: "whisper"
       host: "192.168.0.50"
       port: 10300
     tts:
       engine: "piper"
       host: "192.168.0.50"
       port: 10200
   
   ollama:
     host: "http://192.168.0.50:11434"
     models:
       fast: "llama3.2:3b"
       reasoning: "dolphin-mixtral:8x7b"
   
   memory:
     chromadb:
       host: "192.168.0.50"
       port: 8000
   ```

2. Run Freya with agent architecture:
   ```bash
   python main.py --use-agents --config config/my_config.yaml
   ```

## Network Configuration

All services communicate over the local network:

| Service | Host | Port | Protocol |
|---------|------|------|----------|
| Home Assistant | 192.168.0.50 | 8123 | HTTP |
| Wyoming Whisper | 192.168.0.50 | 10300 | Wyoming |
| Wyoming Piper | 192.168.0.50 | 10200 | Wyoming |
| OpenWakeWord | 192.168.0.50 | 10400 | Wyoming |
| Ollama | 192.168.0.50 | 11434 | HTTP |
| ChromaDB | 192.168.0.50 | 8000 | HTTP |
| Voice PE | 192.168.0.52 | - | ESPHome |

**Firewall Rules:**
Ensure Windows Firewall allows inbound connections on ports 8123, 10200, 10300, 10400, 11434, and 8000.

## Maintenance

### Updating Containers

```powershell
cd C:\AI_Projects\homeassistant
docker-compose pull
docker-compose up -d
```

### Backing Up Configuration

```powershell
# Backup Home Assistant config
xcopy /E /I config config_backup_$(Get-Date -Format "yyyyMMdd")

# Backup Ollama models
docker exec ollama ollama list
```

### Viewing Logs

```powershell
# Home Assistant logs
docker logs -f homeassistant

# Ollama logs
docker logs -f ollama

# All services
docker-compose logs -f
```

### Resetting Services

```powershell
# Restart all services
docker-compose restart

# Rebuild specific service
docker-compose up -d --force-recreate homeassistant

# Complete reset (WARNING: deletes data)
docker-compose down -v
docker-compose up -d
```

## Performance Optimization

### Ollama Model Selection

| Model | VRAM | Speed | Use Case |
|-------|------|-------|----------|
| llama3.2:3b | 2GB | Fast | Quick responses, simple queries |
| dolphin-mixtral:8x7b | 26GB | Medium | Complex reasoning, multi-step tasks |
| deepseek-coder-v2:16b-lite | 10GB | Medium | Code generation, technical questions |

**Recommendation:** Start with `llama3.2:3b` for fast responses. Enable model escalation in Freya config to automatically switch to larger models for complex queries.

### Memory Management

**ChromaDB:**
- Stores conversation history as vector embeddings
- Automatic semantic search for relevant context
- Configure retention policy in Freya config

**Home Assistant:**
- Purge old recorder data: Settings → System → Storage
- Limit history to 7-14 days for better performance

### Wake Word Sensitivity

Adjust in Voice PE ESPHome config:
```yaml
micro_wake_word:
  models:
    - model: /config/custom_wakewords/hey_freya.json
      id: hey_freya
      # Adjust these values
      probability_cutoff: 0.85  # Lower = more sensitive (0.5-0.95)
      sliding_window_size: 5     # Larger = more stable
```

## Security Considerations

1. **Network Isolation**: Consider running Home Assistant on isolated VLAN
2. **API Keys**: Store in `.env` files, never commit to Git
3. **Firewall**: Restrict external access to Home Assistant port 8123
4. **Updates**: Regularly update Docker images for security patches
5. **Backups**: Automate configuration backups to external storage

## Troubleshooting

### Voice PE Not Responding

1. Check device status in ESPHome dashboard
2. Verify network connectivity: `ping 192.168.0.52`
3. Check ESPHome logs for errors
4. Reflash firmware if unresponsive

### Wake Word Not Detected

1. Test microphone: Settings → Voice assistants → Test microphone
2. Adjust wake word sensitivity
3. Retrain custom wake word with more samples
4. Check OpenWakeWord logs: `docker logs wyoming-openwakeword`

### Ollama Not Responding

1. Check container status: `docker ps`
2. Verify model is loaded: `docker exec ollama ollama list`
3. Check GPU availability: `docker exec ollama nvidia-smi`
4. Restart container: `docker restart ollama`

### Home Agent Integration Issues

1. Verify Ollama is accessible from Home Assistant
2. Check Home Agent logs in Home Assistant
3. Reconfigure integration with correct host/port
4. Ensure selected model is pulled in Ollama

## Resources

- **Home Assistant**: https://www.home-assistant.io/
- **ESPHome**: https://esphome.io/
- **Wyoming Protocol**: https://github.com/rhasspy/wyoming
- **Ollama**: https://ollama.ai/
- **microWakeWord**: https://github.com/kahrendt/microWakeWord
- **Training Container**: https://github.com/TaterTotterson/microWakeWord-Trainer-Nvidia-Docker
- **Home Agent**: https://github.com/allenporter/home-agent

## Contributing

This setup is part of the larger Freya project. For contributions:

1. Fork the repository: https://github.com/MrPink1977/freya_project
2. Create feature branch
3. Submit pull request with detailed description

## License

This project follows the same license as the main Freya repository.

---

**Last Updated:** January 2026  
**Maintained By:** MrPink1977  
**Project:** Freya Voice AI Assistant
