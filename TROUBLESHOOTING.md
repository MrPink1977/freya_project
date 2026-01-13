# Troubleshooting Guide

This guide covers common issues with the Freya Home Assistant setup and their solutions.

## Table of Contents

- [Docker & Container Issues](#docker--container-issues)
- [Home Assistant Issues](#home-assistant-issues)
- [Voice PE Device Issues](#voice-pe-device-issues)
- [Wake Word Detection Issues](#wake-word-detection-issues)
- [Ollama & LLM Issues](#ollama--llm-issues)
- [Training Issues](#training-issues)
- [Network & Connectivity Issues](#network--connectivity-issues)
- [Performance Issues](#performance-issues)

---

## Docker & Container Issues

### Containers Won't Start

**Symptoms:**
- `docker-compose up -d` fails
- Containers exit immediately after starting
- "Port already in use" errors

**Solutions:**

1. **Check Docker Desktop is running:**
   ```powershell
   # Restart Docker Desktop from system tray
   ```

2. **Check for port conflicts:**
   ```powershell
   netstat -ano | findstr "8123"  # Check if port is in use
   netstat -ano | findstr "11434"  # Check Ollama port
   ```

3. **View container logs:**
   ```powershell
   docker logs homeassistant
   docker logs ollama
   ```

4. **Restart all containers:**
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

5. **Check WSL2 configuration:**
   ```powershell
   wsl --list --verbose
   # Ensure WSL2 is running
   wsl --shutdown
   # Wait 10 seconds, then restart Docker Desktop
   ```

### Out of Memory Errors

**Symptoms:**
- Containers crash with OOM (Out of Memory) errors
- Docker Desktop shows high memory usage
- System becomes unresponsive

**Solutions:**

1. **Increase WSL2 memory allocation:**
   
   Edit `C:\Users\<YourUsername>\.wslconfig`:
   ```ini
   [wsl2]
   memory=12GB  # Increase if you have 32GB+ RAM
   processors=6
   swap=4GB
   ```

2. **Restart WSL2:**
   ```powershell
   wsl --shutdown
   ```

3. **Reduce Ollama model size:**
   - Use `llama3.2:3b` (2GB) instead of larger models
   - Unload unused models: `docker exec ollama ollama rm <model>`

4. **Disable GPU for Ollama:**
   - Comment out GPU section in `docker-compose.yml`
   - CPU-only mode uses less memory

### Container Keeps Restarting

**Symptoms:**
- Container shows "Restarting" status
- Logs show repeated crashes

**Solutions:**

1. **Check logs for errors:**
   ```powershell
   docker logs --tail 100 <container_name>
   ```

2. **Verify volume mounts exist:**
   ```powershell
   # Ensure directories exist
   mkdir C:\AI_Projects\homeassistant\config
   mkdir C:\AI_Projects\homeassistant\ollama_data
   ```

3. **Check file permissions:**
   - Ensure Docker has access to mounted directories
   - Docker Desktop → Settings → Resources → File Sharing

4. **Recreate container:**
   ```powershell
   docker-compose stop <service_name>
   docker-compose rm <service_name>
   docker-compose up -d <service_name>
   ```

---

## Home Assistant Issues

### Can't Access Home Assistant Web Interface

**Symptoms:**
- `http://192.168.0.50:8123` not loading
- "Connection refused" or timeout errors

**Solutions:**

1. **Check container is running:**
   ```powershell
   docker ps | findstr homeassistant
   ```

2. **Check logs:**
   ```powershell
   docker logs homeassistant --tail 50
   ```

3. **Verify network mode:**
   ```powershell
   docker inspect homeassistant | findstr NetworkMode
   # Should show "host"
   ```

4. **Try localhost:**
   - `http://localhost:8123`
   - If this works, firewall may be blocking external access

5. **Check Windows Firewall:**
   - Windows Security → Firewall & network protection
   - Allow Docker Desktop through firewall
   - Allow port 8123 inbound

6. **Restart container:**
   ```powershell
   docker restart homeassistant
   ```

### Integrations Won't Connect

**Symptoms:**
- Wyoming integrations show "Failed to connect"
- Home Agent integration not working
- "Connection refused" errors

**Solutions:**

1. **Verify services are running:**
   ```powershell
   docker ps
   # Check all Wyoming containers are up
   ```

2. **Test connectivity:**
   ```powershell
   # Test from Windows host
   curl http://192.168.0.50:10300  # Whisper
   curl http://192.168.0.50:10200  # Piper
   curl http://192.168.0.50:11434  # Ollama
   ```

3. **Check container logs:**
   ```powershell
   docker logs wyoming-whisper
   docker logs wyoming-piper
   docker logs ollama
   ```

4. **Use correct host:**
   - If Home Assistant is in host network mode, use `192.168.0.50`
   - If in bridge mode, use container names: `wyoming-whisper`

5. **Reconfigure integration:**
   - Settings → Devices & Services
   - Remove failing integration
   - Re-add with correct host/port

### Voice Assistant Not Working

**Symptoms:**
- Test button does nothing
- No response to voice commands
- "Failed to start conversation" errors

**Solutions:**

1. **Check all components:**
   - Settings → Voice assistants → Edit assistant
   - Verify all fields are filled:
     - Conversation agent: Home Agent
     - STT: Wyoming (Whisper)
     - TTS: Wyoming (Piper)
     - Wake word: Selected

2. **Test microphone:**
   - Settings → Voice assistants → Test microphone
   - Speak and verify waveform appears

3. **Test STT separately:**
   - Use Wyoming Whisper test tool
   - Check logs: `docker logs wyoming-whisper`

4. **Test TTS separately:**
   - Use Wyoming Piper test tool
   - Check logs: `docker logs wyoming-piper`

5. **Check Home Agent:**
   - Verify Ollama is running and model is loaded
   - Test Ollama directly: `curl http://192.168.0.50:11434/api/tags`

---

## Voice PE Device Issues

### Device Not Appearing in ESPHome

**Symptoms:**
- Voice PE not showing up in ESPHome dashboard
- Can't adopt device
- "Device not found" errors

**Solutions:**

1. **Check device is powered on:**
   - LED ring should light up on boot
   - Listen for boot sound (if configured)

2. **Check WiFi connection:**
   - Verify device is on same network as Home Assistant
   - Check router DHCP leases for device MAC address
   - Try connecting to device's fallback hotspot

3. **Check ESPHome logs:**
   - Settings → System → Logs
   - Filter by "esphome"

4. **Manually add device:**
   - ESPHome dashboard → Add Device
   - Enter device IP address manually
   - Adopt device

5. **Reflash firmware:**
   - Connect device via USB
   - ESPHome → Edit → Install → Plug into this computer
   - Flash new firmware

### Device Keeps Disconnecting

**Symptoms:**
- Device shows "Offline" frequently
- Intermittent connectivity
- "Connection lost" in logs

**Solutions:**

1. **Check WiFi signal strength:**
   - Device sensors → WiFi Signal
   - Should be > -70 dBm
   - Move device closer to router or add WiFi extender

2. **Check power supply:**
   - Use quality USB power adapter (5V 2A minimum)
   - Try different USB cable
   - Avoid USB hubs

3. **Reduce log level:**
   - Edit ESPHome config
   - Change `logger: level: DEBUG` to `level: WARN`
   - Reduces CPU load

4. **Disable web server:**
   - Comment out `web_server:` in ESPHome config
   - Saves memory and reduces crashes

5. **Check for memory leaks:**
   - Monitor uptime sensor
   - If device crashes after specific time, may be memory leak
   - Update ESPHome to latest version

### Device Not Responding to Commands

**Symptoms:**
- Can see device in Home Assistant
- Can't control device (mute, volume, etc.)
- Commands timeout

**Solutions:**

1. **Check API connection:**
   - ESPHome logs should show "API connection established"
   - Verify encryption key matches in Home Assistant

2. **Restart device:**
   - ESPHome dashboard → Device → Restart

3. **Check for firmware errors:**
   - ESPHome logs → Look for errors or warnings
   - Update to latest ESPHome version

4. **Verify configuration:**
   - ESPHome → Edit → Validate
   - Fix any configuration errors

---

## Wake Word Detection Issues

### Wake Word Not Detected

**Symptoms:**
- Voice PE doesn't respond to wake word
- No LED feedback when saying wake word
- Logs don't show wake word detection

**Solutions:**

1. **Check microphone:**
   - Test in Home Assistant: Settings → Voice assistants → Test
   - Verify microphone is working in ESPHome logs

2. **Adjust sensitivity:**
   
   Edit ESPHome config:
   ```yaml
   micro_wake_word:
     models:
       - model: /config/custom_wakewords/hey_freya.json
         id: hey_freya
         probability_cutoff: 0.70  # Lower = more sensitive (was 0.85)
   ```

3. **Check model is loaded:**
   - ESPHome logs should show "Loaded wake word model: hey_freya"
   - Verify files exist in `/config/custom_wakewords/`

4. **Test with default wake word:**
   - Temporarily switch to "hey_jarvis" or "alexa"
   - If default works, issue is with custom model

5. **Retrain custom wake word:**
   - Record more diverse samples
   - Include different distances, volumes, tones
   - See training guide for details

6. **Check for interference:**
   - Reduce background noise
   - Move away from speakers during detection
   - Test in quiet environment

### Too Many False Positives

**Symptoms:**
- Wake word triggers randomly
- Activates from TV, music, or conversation
- Too sensitive

**Solutions:**

1. **Increase probability cutoff:**
   ```yaml
   probability_cutoff: 0.90  # Higher = less sensitive (was 0.85)
   ```

2. **Increase sliding window:**
   ```yaml
   sliding_window_size: 10  # Larger = more stable (was 5)
   ```

3. **Retrain with negative samples:**
   - Include samples of similar-sounding phrases
   - Train model to distinguish wake word from common phrases

4. **Adjust microphone gain:**
   - Reduce microphone sensitivity in ESPHome config
   - Lower gain reduces pickup of distant sounds

### Custom Wake Word Won't Load

**Symptoms:**
- ESPHome compilation fails
- "Model not found" errors
- Device boots but wake word doesn't work

**Solutions:**

1. **Verify file paths:**
   ```
   C:\AI_Projects\homeassistant\config\custom_wakewords\hey_freya.tflite
   C:\AI_Projects\homeassistant\config\custom_wakewords\hey_freya.json
   ```

2. **Check file format:**
   - `.tflite` file should be microWakeWord format (not openWakeWord)
   - `.json` manifest should match model name

3. **Verify JSON manifest:**
   ```json
   {
     "type": "micro",
     "model": "hey_freya",
     "version": 1,
     "probability_cutoff": 0.85,
     "sliding_window_size": 5
   }
   ```

4. **Check ESPHome version:**
   - Update to latest ESPHome version
   - Older versions may not support custom models

5. **Test model locally:**
   - Use microWakeWord test script to verify model works
   - Ensure model was trained correctly

---

## Ollama & LLM Issues

### Ollama Not Responding

**Symptoms:**
- Home Agent shows "Connection failed"
- `curl http://192.168.0.50:11434` times out
- Container is running but not responding

**Solutions:**

1. **Check container logs:**
   ```powershell
   docker logs ollama --tail 100
   ```

2. **Verify model is loaded:**
   ```powershell
   docker exec ollama ollama list
   # Should show installed models
   ```

3. **Test API directly:**
   ```powershell
   curl http://192.168.0.50:11434/api/tags
   ```

4. **Restart container:**
   ```powershell
   docker restart ollama
   ```

5. **Check GPU availability (if using):**
   ```powershell
   docker exec ollama nvidia-smi
   # Should show GPU info
   ```

6. **Try CPU-only mode:**
   - Comment out GPU section in `docker-compose.yml`
   - Restart container

### Model Download Fails

**Symptoms:**
- `ollama pull` hangs or fails
- "Connection reset" errors
- Partial downloads

**Solutions:**

1. **Check internet connection:**
   ```powershell
   docker exec ollama ping -c 4 ollama.ai
   ```

2. **Check disk space:**
   ```powershell
   docker exec ollama df -h
   # Ensure sufficient space for model
   ```

3. **Retry with timeout:**
   ```powershell
   docker exec ollama ollama pull llama3.2:3b --timeout 600
   ```

4. **Pull from different network:**
   - Try from different WiFi or wired connection
   - Some networks may block large downloads

5. **Download manually:**
   - Download model file from Ollama website
   - Import manually: `ollama create <model> -f Modelfile`

### Responses Are Slow

**Symptoms:**
- Long delays before response
- Slow token generation
- High CPU/GPU usage

**Solutions:**

1. **Use smaller model:**
   ```powershell
   docker exec ollama ollama pull llama3.2:3b  # Faster than 8x7b
   ```

2. **Enable GPU acceleration:**
   - Uncomment GPU section in `docker-compose.yml`
   - Requires NVIDIA GPU with CUDA support

3. **Reduce context length:**
   - Configure Home Agent to use shorter context
   - Limits conversation history

4. **Increase Docker resources:**
   - Docker Desktop → Settings → Resources
   - Increase CPU and memory allocation

5. **Close other applications:**
   - Free up system resources
   - Disable background tasks during use

---

## Training Issues

### Training Process Crashes

**Symptoms:**
- Jupyter kernel dies during training
- "Out of memory" errors
- System becomes unresponsive

**Solutions:**

1. **Reduce MAX_SAMPLES:**
   ```python
   MAX_SAMPLES = 10000  # Reduce from 50000
   ```

2. **Increase WSL2 memory:**
   ```ini
   [wsl2]
   memory=16GB  # Increase from 12GB
   ```

3. **Use CPU-only training:**
   ```powershell
   # Remove --gpus flag
   docker run --rm -it -p 8888:8888 -v ${PWD}:/data ghcr.io/tatertotterson/microwakeword:latest
   ```

4. **Close other applications:**
   - Stop Home Assistant containers during training
   - Free up memory: `docker-compose stop`

5. **Monitor memory usage:**
   ```powershell
   # In WSL
   watch -n 1 free -h
   ```

### Sample Generation Fails

**Symptoms:**
- Piper TTS errors during sample generation
- "Failed to generate sample" messages
- Empty `generated_samples/` directory

**Solutions:**

1. **Check Piper installation:**
   - Verify Piper is installed in training container
   - Check Jupyter logs for errors

2. **Use different voice:**
   ```python
   PIPER_VOICE = "en_US-lessac-medium"  # Try different voice
   ```

3. **Reduce batch size:**
   ```python
   BATCH_SIZE = 50  # Reduce from 100
   ```

4. **Generate samples manually:**
   - Use external TTS service
   - Place .wav files in `generated_samples/`

### Training Takes Too Long

**Symptoms:**
- Training runs for 8+ hours
- Progress is very slow
- CPU at 100% constantly

**Solutions:**

1. **Use GPU acceleration:**
   ```powershell
   docker run --rm -it --gpus all -p 8888:8888 -v ${PWD}:/data ghcr.io/tatertotterson/microwakeword:latest
   ```

2. **Reduce training samples:**
   ```python
   MAX_SAMPLES = 5000  # Minimum for decent accuracy
   ```

3. **Reduce epochs:**
   ```python
   EPOCHS = 10  # Reduce from 20
   ```

4. **Use faster machine:**
   - Training on dedicated machine with GPU
   - Cloud instance with GPU (AWS, GCP, Azure)

### Trained Model Doesn't Work

**Symptoms:**
- Model loads but doesn't detect wake word
- Very low accuracy
- False positives everywhere

**Solutions:**

1. **Retrain with more samples:**
   ```python
   MAX_SAMPLES = 20000  # Increase for better accuracy
   ```

2. **Add personal voice samples:**
   - Record 20-50 samples of your voice
   - Place in `personal_samples/` directory
   - Retrain with mixed samples

3. **Adjust training parameters:**
   ```python
   LEARNING_RATE = 0.0001  # Reduce for more stable training
   BATCH_SIZE = 64  # Adjust batch size
   ```

4. **Verify model format:**
   - Ensure output is `.tflite` (not `.h5` or `.pb`)
   - Check JSON manifest is correct

5. **Test model locally:**
   - Use microWakeWord test script
   - Verify model detects wake word before deploying

---

## Network & Connectivity Issues

### Services Can't Communicate

**Symptoms:**
- Home Assistant can't reach Ollama
- Wyoming services unreachable
- "Connection refused" errors

**Solutions:**

1. **Check all containers are on same network:**
   ```powershell
   docker network inspect bridge
   # Or use host network mode for all
   ```

2. **Use correct hostnames:**
   - Host network: Use `192.168.0.50` or `localhost`
   - Bridge network: Use container names (`ollama`, `wyoming-whisper`)

3. **Check firewall rules:**
   - Windows Firewall may block inter-container communication
   - Allow Docker through firewall

4. **Test connectivity:**
   ```powershell
   # From one container to another
   docker exec homeassistant ping ollama
   docker exec homeassistant curl http://ollama:11434
   ```

5. **Use host network mode:**
   - Add `network_mode: host` to all services in `docker-compose.yml`
   - Simplifies networking but exposes all ports

### Voice PE Can't Reach Home Assistant

**Symptoms:**
- Device shows "API connection failed"
- Can't adopt device
- Device appears offline

**Solutions:**

1. **Check network connectivity:**
   ```powershell
   ping 192.168.0.52  # Voice PE IP
   ```

2. **Verify Home Assistant is accessible:**
   ```powershell
   curl http://192.168.0.50:8123
   ```

3. **Check ESPHome API port:**
   - Default is 6053
   - Ensure not blocked by firewall

4. **Verify encryption key:**
   - ESPHome config must match Home Assistant
   - Regenerate if needed

5. **Check router settings:**
   - Ensure devices are on same VLAN
   - Check for AP isolation (disable if enabled)
   - Verify DHCP reservations

---

## Performance Issues

### High CPU Usage

**Symptoms:**
- Docker Desktop using 90%+ CPU
- System slow and unresponsive
- Fans running constantly

**Solutions:**

1. **Limit CPU for containers:**
   ```yaml
   # In docker-compose.yml
   services:
     ollama:
       cpus: 4  # Limit to 4 cores
   ```

2. **Use smaller LLM models:**
   - Switch from `dolphin-mixtral:8x7b` to `llama3.2:3b`

3. **Reduce concurrent operations:**
   - Don't train wake word while running Home Assistant
   - Stop unused containers

4. **Check for runaway processes:**
   ```powershell
   docker stats
   # Identify container using most CPU
   ```

### High Memory Usage

**Symptoms:**
- System running out of RAM
- Containers being killed (OOM)
- Swap usage very high

**Solutions:**

1. **Limit memory for containers:**
   ```yaml
   # In docker-compose.yml
   services:
     ollama:
       mem_limit: 4g  # Limit to 4GB
   ```

2. **Unload unused Ollama models:**
   ```powershell
   docker exec ollama ollama rm dolphin-mixtral:8x7b
   ```

3. **Reduce ChromaDB cache:**
   - Configure smaller cache size in ChromaDB settings

4. **Increase swap:**
   ```ini
   # .wslconfig
   [wsl2]
   swap=8GB  # Increase swap space
   ```

### Slow Response Times

**Symptoms:**
- Long delays in voice responses
- Laggy web interface
- Timeouts

**Solutions:**

1. **Use faster LLM model:**
   - `llama3.2:3b` is much faster than larger models

2. **Enable GPU acceleration:**
   - Requires NVIDIA GPU
   - Uncomment GPU section in `docker-compose.yml`

3. **Reduce context length:**
   - Shorter conversation history = faster responses

4. **Optimize network:**
   - Use wired connection instead of WiFi
   - Reduce network latency

5. **Upgrade hardware:**
   - More RAM, faster CPU, add GPU
   - SSD instead of HDD for Docker volumes

---

## Getting Help

If you've tried the solutions above and still have issues:

1. **Check logs:**
   ```powershell
   docker logs <container_name> --tail 100
   ```

2. **Enable debug logging:**
   - Home Assistant: `logger: default: debug`
   - ESPHome: `logger: level: DEBUG`

3. **Search existing issues:**
   - GitHub: https://github.com/MrPink1977/freya_project/issues
   - Home Assistant Community: https://community.home-assistant.io/

4. **Create new issue:**
   - Include logs, configuration, and error messages
   - Describe steps to reproduce
   - Mention what you've already tried

5. **Join community:**
   - ESPHome Discord: https://discord.gg/KhAMKrd
   - Home Assistant Discord: https://discord.gg/home-assistant

---

**Last Updated:** January 2026  
**Maintained By:** MrPink1977
