# Quick Start: Freya with Home Assistant

This guide will get you up and running with Freya and Home Assistant in under 30 minutes.

## Prerequisites

- Windows 10/11 with WSL2 enabled
- Docker Desktop installed
- 16GB+ RAM (12GB allocated to Docker)
- Voice PE device (or compatible ESP32 hardware)

## Step 1: Configure WSL2 (5 minutes)

Create `C:\Users\<YourUsername>\.wslconfig`:

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

## Step 2: Setup Directory Structure (2 minutes)

```powershell
# Create project directory
mkdir C:\AI_Projects\homeassistant
cd C:\AI_Projects\homeassistant

# Create subdirectories
mkdir config, whisper_data, piper_data, openwakeword_data, ollama_data, chroma_data, microwakeword_training
mkdir config\custom_wakewords
```

## Step 3: Download Docker Compose File (1 minute)

Copy the `docker-compose.homeassistant.yml` from this repository to `C:\AI_Projects\homeassistant\docker-compose.yml`

Or create it manually with the content from the file.

## Step 4: Start Services (5 minutes)

```powershell
cd C:\AI_Projects\homeassistant
docker-compose up -d
```

Wait for all containers to start:
```powershell
docker ps
```

You should see 6 containers running:
- homeassistant
- wyoming-whisper
- wyoming-piper
- wyoming-openwakeword
- ollama
- chromadb

## Step 5: Install Ollama Models (10 minutes)

```powershell
# Install fast model (required)
docker exec -it ollama ollama pull llama3.2:3b

# Install reasoning model (optional, 26GB)
docker exec -it ollama ollama pull dolphin-mixtral:8x7b

# Install code model (optional, 10GB)
docker exec -it ollama ollama pull deepseek-coder-v2:16b-lite
```

## Step 6: Configure Home Assistant (5 minutes)

1. Open browser: `http://localhost:8123` (or `http://192.168.0.50:8123`)
2. Complete initial setup wizard (create account, set location)
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search and add:
   - **Wyoming Protocol** (Whisper) - Host: `192.168.0.50`, Port: `10300`
   - **Wyoming Protocol** (Piper) - Host: `192.168.0.50`, Port: `10200`
   - **Wyoming Protocol** (OpenWakeWord) - Host: `192.168.0.50`, Port: `10400`
   - **Home Agent** - Host: `http://192.168.0.50:11434`, Model: `llama3.2:3b`

5. Create Voice Assistant:
   - Settings → **Voice assistants** → **Add assistant**
   - Name: "Freya"
   - Conversation agent: **Home Agent**
   - Speech-to-text: **Wyoming (Whisper)**
   - Text-to-speech: **Wyoming (Piper)**
   - Wake word: **Hey Jarvis** (or custom)

## Step 7: Setup Voice PE Device (5 minutes)

### If you already have a Voice PE device:

1. Go to **Settings** → **Devices & Services** → **ESPHome**
2. Your device should appear automatically
3. Click **Adopt** to take control
4. Device will appear in ESPHome dashboard

### If you need to flash a new ESP32:

1. Install ESPHome add-on in Home Assistant
2. Create new device with Voice PE template
3. Flash via USB cable
4. Device will connect to WiFi and appear in dashboard

## Step 8: Test Voice Assistant (2 minutes)

1. Go to **Settings** → **Voice assistants**
2. Click on "Freya"
3. Click **Test** button
4. Speak into your microphone: "What time is it?"
5. You should hear Freya respond!

## Step 9: Clone Freya Repository (Optional)

To use the advanced agent-based system with memory and tools:

```bash
git clone https://github.com/MrPink1977/freya_project.git
cd freya_project
pip install -e .
```

Configure Freya to use Home Assistant services:

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

Run Freya:
```bash
python main.py --use-agents --config config/my_config.yaml
```

## Verification Checklist

- [ ] All 6 Docker containers running (`docker ps`)
- [ ] Home Assistant accessible at `http://192.168.0.50:8123`
- [ ] Ollama models installed (`docker exec ollama ollama list`)
- [ ] Wyoming integrations configured in Home Assistant
- [ ] Voice assistant "Freya" created
- [ ] Voice PE device adopted and online
- [ ] Test conversation successful

## Next Steps

### Train Custom Wake Word "Hey Freya"

See [HOME_ASSISTANT_SETUP.md](HOME_ASSISTANT_SETUP.md#custom-wake-word-training) for detailed training instructions.

**Quick version:**
1. `cd C:\AI_Projects\homeassistant\microwakeword_training`
2. `docker run --rm -it -p 8888:8888 -v ${PWD}:/data ghcr.io/tatertotterson/microwakeword:latest`
3. Open `http://localhost:8888`
4. Edit notebook: `TARGET_WORD = "hey_freya"`, `MAX_SAMPLES = 10000`
5. Run all cells (1-4 hours)
6. Copy `hey_freya.tflite` and `hey_freya.json` to `config/custom_wakewords/`
7. Update Voice PE ESPHome config to use new wake word

### Explore Advanced Features

- **Memory System**: Freya remembers conversations using ChromaDB
- **Tool Execution**: Time, calculator, file operations, web search
- **Model Escalation**: Automatically switches to larger models for complex queries
- **Vision Integration**: Add camera support for facial recognition
- **Home Automation**: Control lights, switches, sensors via natural language

### Customize Configuration

Edit `C:\AI_Projects\homeassistant\config\configuration.yaml` to:
- Add devices and integrations
- Create automations
- Configure scenes and scripts
- Set up dashboards

## Troubleshooting

### Docker containers won't start
```powershell
# Check Docker Desktop is running
# Restart Docker Desktop
# Check WSL2 is configured correctly
wsl --list --verbose
```

### Home Assistant not accessible
```powershell
# Check container logs
docker logs homeassistant

# Verify network mode is host
docker inspect homeassistant | findstr NetworkMode
```

### Ollama models won't download
```powershell
# Check internet connectivity
# Verify container is running
docker logs ollama

# Try pulling manually
docker exec -it ollama ollama pull llama3.2:3b
```

### Voice PE device not connecting
- Check WiFi credentials in ESPHome config
- Verify device is powered on
- Check router DHCP leases for device IP
- Reflash firmware if unresponsive

### Wake word not detected
- Test microphone in Home Assistant
- Adjust wake word sensitivity
- Check OpenWakeWord logs: `docker logs wyoming-openwakeword`
- Retrain custom wake word with more samples

## Support

For issues and questions:
- **GitHub Issues**: https://github.com/MrPink1977/freya_project/issues
- **Home Assistant Community**: https://community.home-assistant.io/
- **ESPHome Discord**: https://discord.gg/KhAMKrd

## Resources

- [Full Setup Guide](HOME_ASSISTANT_SETUP.md)
- [Main README](README.md)
- [Home Assistant Documentation](https://www.home-assistant.io/docs/)
- [ESPHome Documentation](https://esphome.io/)
- [Wyoming Protocol](https://github.com/rhasspy/wyoming)

---

**Estimated Total Time**: 30-45 minutes (excluding model downloads and wake word training)
