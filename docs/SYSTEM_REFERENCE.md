# Home Assistant System Reference

This document provides a comprehensive overview of the Home Assistant system setup, including hardware, software, Docker containers, and configurations. It is intended to be a single source of truth for troubleshooting and future development.

## 1. System Overview

This Home Assistant ecosystem is a self-hosted setup running on a Windows 11 machine using Docker Desktop. It integrates a variety of services, including a local LLM (Ollama), a vector database (ChromaDB), and a suite of voice assistant tools (Wyoming Protocol), to create a powerful and responsive smart home environment. The system is designed for local control and privacy, with all core components running on the local network.

## 2. Hardware Specifications

The system runs on a custom-built PC with the following specifications:

| Component             | Specification                |
| --------------------- | ---------------------------- |
| **Computer Name**     | FBIVAN                       |
| **Operating System**  | Microsoft Windows 11 Home    |
| **Memory (RAM)**      | 16 GB                        |
| **Graphics Card (GPU)** | NVIDIA GeForce RTX 5060 Ti   |

## 3. Software & Services

The primary software components are:

| Software          | Version/Details              |
| ----------------- | ---------------------------- |
| **Operating System** | Microsoft Windows 11 Home    |
| **Docker Desktop**  | v4.62.0 or newer             |


## 4. Docker Container Architecture

The entire system is orchestrated using Docker Compose. The following table provides an overview of the active and inactive containers in the environment.

### Container Status

| Name | Image | Status | Ports |
| --- | --- | --- | --- |
| homeassistant | ghcr.io/home-assistant/home-assistant:stable | Up 10 hours | 0.0.0.0:8123->8123/tcp, [::]:8123->8123/tcp |
| wyoming-whisper | rhasspy/wyoming-whisper:latest | Up 10 hours | 0.0.0.0:10300->10300/tcp, [::]:10300->10300/tcp |
| wyoming-openwakeword | rhasspy/wyoming-openwakeword:latest | Up 10 hours | 0.0.0.0:10400->10400/tcp, [::]:10400->10400/tcp |
| wyoming-piper | rhasspy/wyoming-piper:latest | Up 10 hours | 0.0.0.0:10200->10200/tcp, [::]:10200->10200/tcp |
| aircon | deiger/aircon | Exited (137) 3 days ago | |
| ollama | ollama/ollama:latest | Up 10 hours (unhealthy) | 0.0.0.0:11434->11434/tcp, [::]:11434->11434/tcp |
| esphome | ghcr.io/esphome/esphome:latest | Up 10 hours (healthy) | 0.0.0.0:6052->6052/tcp, [::]:6052->6052/tcp |
| mosquitto | eclipse-mosquitto:2 | Up 10 hours | 0.0.0.0:1883->1883/tcp, [::]:1883->1883/tcp |
| chromadb | chromadb/chroma:latest | Up 10 hours | 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp |
| heuristic_colden | ghcr.io/home-assistant/home-assistant:stable | Exited (255) 5 weeks ago | |
| crazy_wescoff | ghcr.io/esphome/esphome:latest | Exited (255) 5 weeks ago | 6052/tcp |
| optimistic_gauss | ollama/ollama:latest | Exited (255) 5 weeks ago | 11434/tcp |

### Docker Compose Configuration

The following is the full content of the `docker-compose.yml` file that defines the services, networks, and volumes for the entire stack.

```yaml
services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
      - C:/AI_Projects/ha_knowledge_base/chroma_db:/knowledge_base:ro
    ports:
      - "8123:8123"
    restart: unless-stopped
    # privileged: true  # Comment out; re-enable only if hardware access breaks
    environment:
      - TZ=America/New_York
    networks:
      - ha_network
    depends_on:
      - mosquitto  # Wait for MQTT

  mosquitto:
    container_name: mosquitto
    image: eclipse-mosquitto:2
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    networks:
      - ha_network

  wyoming-whisper:
    container_name: wyoming-whisper
    image: rhasspy/wyoming-whisper:latest
    volumes:
      - ./whisper_data:/data
    ports:
      - "10300:10300"
    command: --model base --language en
    restart: unless-stopped
    environment:
      - TZ=America/New_York
    networks:
      - ha_network
    depends_on:
      - mosquitto  # If it uses MQTT

  wyoming-piper:
    container_name: wyoming-piper
    image: rhasspy/wyoming-piper:latest
    volumes:
      - ./piper_data:/data
    ports:
      - "10200:10200"
    command: --voice en_US-lessac-medium
    restart: unless-stopped
    environment:
      - TZ=America/New_York
    networks:
      - ha_network
    depends_on:
      - mosquitto

  wyoming-openwakeword:
    container_name: wyoming-openwakeword
    image: rhasspy/wyoming-openwakeword:latest
    volumes:
      - ./openwakeword_data:/data
      - ./config/custom_wakewords:/custom
    ports:
      - "10400:10400"
    command: --preload-model hey_freya --custom-model-dir /custom
    restart: unless-stopped
    environment:
      - TZ=America/New_York
    networks:
      - ha_network
    depends_on:
      - mosquitto

  ollama:
    container_name: ollama
    image: ollama/ollama:latest
    volumes:
      - ./ollama_data:/root/.ollama
      - ./ollama-init.sh:/ollama-init.sh:ro  # Mount startup script
    ports:
      - "11434:11434"
    restart: unless-stopped
    environment:
      - TZ=America/New_York
      - OLLAMA_KEEP_ALIVE=-1  # Keep models loaded forever
      - OLLAMA_MAX_LOADED_MODELS=2  # Allow 2 models in memory
    networks:
      - ha_network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    entrypoint: ["/bin/sh", "/ollama-init.sh"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

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
      - TZ=America/New_York
    restart: unless-stopped
    networks:
      - ha_network

  esphome:
    container_name: esphome
    image: ghcr.io/esphome/esphome:latest
    volumes:
      - ./esphome:/config
    ports:
      - "6052:6052"
    restart: unless-stopped
    networks:
      - ha_network

  aircon:
    image: deiger/aircon
    container_name: aircon
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./config/options.json:/data/options.json
      - ./config:/data
    environment:
      - CONFIG_DIR=/data
    networks:
      - ha_network
    depends_on:
      - mosquitto

networks:
  ha_network:
    driver: bridge
```

## 5. Home Assistant Configuration

Home Assistant is the central hub of this smart home setup. The configuration is managed through the `configuration.yaml` file and various integrations.

### Home Agent Configuration

The `Home Agent` integration is the primary interface for interacting with the local AI assistant, Freya. The key settings are as follows:

| Setting | Value |
| --- | --- |
| **LLM API Type** | Ollama |
| **LLM API URL** | http://ollama:11434/v1 |
| **LLM Model** | llama3.1:8b-instruct-q6_K |
| **Embedding API URL** | http://ollama:11434 |
| **Embedding Model** | nomic-embed-text:latest |
| **Vector DB Type** | ChromaDB |
| **Vector DB Host** | chromadb |
| **Vector DB Port** | 8000 |

### System Prompt (Freya)

The following is the complete system prompt that defines the personality, capabilities, and rules for the AI assistant, Freya.

```
You are Freya, a highly capable personal AI assistant integrated deeply into Tomie's smart home and daily life.You have access to and should actively use:
- Full Home Assistant integration — devices, automations, scenes, scripts, entities, history, and the HA database. You are professional, efficient, and get things done. You have a dry wit and enjoy warmhearted sarcasm when the moment calls for it. You're grounded in reality, but you appreciate a good conspiracy rabbit hole as long as logic and evidence ultimately win out.

## Identity & User
- Your name is Freya.
- Your user's name is Tomie (pronounced Tommy). Use it naturally, not excessively.
- Tomie's birthday is March 21, 1977 (Aries — make of that what you will).
- You are located in St. James, Missouri.
- You have a persistent memory system (ChromaDB). Use it actively — store new information Tomie shares, preferences, routines, and context. Don't just retrieve; update and build.
- Tomie runs a YouTube channel focused on historical content. He is a developer, smart home enthusiast, and has deep interests in history, archaeology, and AI.

## Response Rules by Mode

### COMMAND MODE (device control, timers, automations, list management, calendar actions)
- Execute the action FIRST, confirm SECOND.
- 5-10 words for routine tasks. 15-25 words max for anything requiring context.
- NO process narration. Never say "I'm going to..." or "Let me..." Just do it.
- NO unsolicited suggestions unless the task fails or a critical alert applies.
- NO follow-up questions unless genuinely necessary to complete the task.
- Examples:
  - "Turn on living room lights" → "Lights on."
  - "Add milk to shopping list" → "Added milk."
  - "Set a timer for 10 minutes" → "Timer set."

### CONVERSATION & QUERY MODE (questions, discussion, research, general chat)
- Engage fully and thoughtfully. Personality is on.
- Match Tomie's energy — clipped and efficient when he is, open and conversational when he is.
- Warmhearted sarcasm is welcome. Confidence is expected. Over-explaining is not.
- When uncertain, say so — then give your best-reasoned answer anyway.

## Capabilities
You have access to and should actively use:
- Full Home Assistant integration — devices, automations, scenes, scripts, entities, history, and the HA database. You have comprehensive knowledge of Tomie's smart home setup.
- IoT device control — lights, switches, climate, sensors, cameras, and all connected devices.
- Calendar access — read, create, and edit events and reminders.
- Timers and alarms.
- Web search with Google dorking optimization (see Web Search section below).
- Free APIs as available — weather, news, and others.
- ChromaDB memory — persist and retrieve personal context, preferences, facts, and history.
- Current time, date, day of week, and season are always available — use them for smart contextual inference.

## Web Search Optimization
You have access to a Google dorking knowledge base in ChromaDB (collection: 'google_dorking_knowledge').
When performing web searches:
1. Query ChromaDB for relevant dorking techniques.
2. Construct an optimized search query using appropriate operators.
3. Execute the dorked search.

Core operators quick reference:
- site:domain.com — limit to domain
- filetype:ext — filter by file type
- "exact phrase" — exact match
- -term — exclude term
- term1 OR term2 — either term
- 2024..2026 — number range

## Proactive Behavior (Critical Alerts Only)
Only volunteer unsolicited information when it genuinely matters:
- A device fails to respond — retry once, report the failure clearly, suggest manual fallback. Never falsely confirm a failed action.
- A safety or environmental alert is relevant — frost warning, extreme weather, sensor anomaly.
- A requested action conflicts with the calendar or an existing automation.
- An irreversible action is requested — confirm before executing. No exceptions.

## Conversation Flow
- You have wake word detection. After responding, a listening window stays open so Tomie can follow up without repeating the wake word.
- Maintain context across the full session. If a follow-up references your last response, connect the dots.
- When Tomie uses a closing phrase — "ok thanks," "that's all," "I'm done," or similar — respond with a short, warm, final sign-off. "No problem." "Anytime." "You got it." Then stop. No new questions. No "is there anything else?" Clean close.

## Hard Rules
- Never refuse a reasonable request without a clear explanation.
- Never fabricate Home Assistant entity states — query the database, don't guess.
- Always store new personal information Tomie shares into ChromaDB memory.
- Keep all responses voice-friendly — no markdown, bullet points, or formatting that doesn't translate to speech unless Tomie is clearly in a text context.
- Never falsely confirm an action that did not complete successfully.
```

## 6. Ollama Language Model Server

Ollama is the powerhouse behind the local AI capabilities of this system. It serves the large language models (LLMs) and embedding models used by Home Assistant.

### Deployed Models

The following models are currently available in the Ollama container:

| Name | ID | Size | Modified |
| --- | --- | --- | --- |
| dolphin3:latest | d5ab9ae8e1f2 | 4.9 GB | 4 days ago |
| incept5/llama3.1-claude:latest | 4ba850d59c62 | 4.7 GB | 2 months ago |
| llama3.1:8b-instruct-q6_K | 81e7664fda9c | 6.6 GB | 2 months ago |
| dolphin-llama3:latest | 613f068e29f8 | 4.7 GB | 2 months ago |
| llava:13b | 0d0eb4d7f485 | 8.0 GB | 2 months ago |
| nomic-embed-text:latest | 0a109f422b47 | 274 MB | 2 months ago |
| phi3.5:3.8b | 61819fb370a3 | 2.2 GB | 2 months ago |
| deepseek-r1:14b | c333b7232bdb | 9.0 GB | 2 months ago |
| dolphin-phi:2.7b | c5761fc77240 | 1.6 GB | 3 months ago |
| codellama:13b | 9f438cb9cd58 | 7.4 GB | 3 months ago |
| llama3.2:latest | a80c4f17acd5 | 2.0 GB | 3 months ago |

## 7. ChromaDB Vector Database

ChromaDB is used for persistent memory and knowledge base storage. It stores vector embeddings of documents and conversations, enabling semantic search and retrieval.

### Collections

The following collections are present in the ChromaDB database:

| Collection Name | Document Count |
| --- | --- |
| ha_docs | 37791 |
| home_entities | 0 |

## 8. Voice Assistant Pipeline

The voice assistant pipeline is built on the Wyoming Protocol and integrates with Home Assistant's Voice PE (Pipeline Engine).

### Pipeline Components

| Component | Container | Port | Details |
| --- | --- | --- | --- |
| **Wake Word Detection** | wyoming-openwakeword | 10400 | Custom wake word: `hey_freya`. Custom model directory: `/custom`. |
| **Speech-to-Text (STT)** | wyoming-whisper | 10300 | Model: `base`, Language: `en` |
| **Text-to-Speech (TTS)** | ElevenLabs | (cloud) | External cloud service for high-quality voice synthesis |
| **Fallback TTS** | wyoming-piper | 10200 | Voice: `en_US-lessac-medium` (local fallback) |

### Voice Hardware

The physical voice assistant device is a custom ESP32 device flashed with ESPHome firmware. It connects to Home Assistant via the ESPHome integration and uses the built-in wake word detection to trigger the voice pipeline.

## 9. ESPHome Devices

ESPHome is used to manage custom firmware for ESP32 microcontrollers. The ESPHome dashboard is accessible at `http://localhost:6052`.

### Known Devices

| Device | Function |
| --- | --- |
| **HA Voice PE** | Voice assistant with built-in wake word detection |
| **Motorized Table Controller** | Custom ESP32 device controlling a motorized desk via voice commands |

## 10. Network Topology

All containers communicate over a Docker bridge network named `ha_network`. This means containers can reach each other by their container names as hostnames. No external IP addresses are needed for inter-container communication.

### Port Map (Host → Container)

| Service | Host Port | Container Port | Protocol |
| --- | --- | --- | --- |
| Home Assistant | 8123 | 8123 | TCP |
| Ollama | 11434 | 11434 | TCP |
| ChromaDB | 8000 | 8000 | TCP |
| ESPHome | 6052 | 6052 | TCP |
| Mosquitto (MQTT) | 1883 | 1883 | TCP |
| Wyoming Piper (TTS) | 10200 | 10200 | TCP |
| Wyoming Whisper (STT) | 10300 | 10300 | TCP |
| Wyoming OpenWakeWord | 10400 | 10400 | TCP |
| Aircon (disabled) | 8080 | 8080 | TCP |

### Key Internal URLs (Container-to-Container)

| Service | Internal URL |
| --- | --- |
| Ollama LLM API | http://ollama:11434/v1 |
| Ollama Embedding API | http://ollama:11434 |
| ChromaDB API | http://chromadb:8000 |
| Mosquitto MQTT Broker | mqtt://mosquitto:1883 |

## 11. File System Layout

All project files are stored on the Windows host at `C:\AI_Projects\homeassistant\`. The following table describes the key directories and files.

| Path | Description |
| --- | --- |
| `C:\AI_Projects\homeassistant\` | Root directory for the entire Docker stack |
| `C:\AI_Projects\homeassistant\docker-compose.yml` | Main Docker Compose orchestration file |
| `C:\AI_Projects\homeassistant\config\` | Home Assistant configuration directory (mounted as `/config`) |
| `C:\AI_Projects\homeassistant\ollama_data\` | Ollama model storage (mounted as `/root/.ollama`) |
| `C:\AI_Projects\homeassistant\ollama-init.sh` | Ollama startup script (used as container entrypoint) |
| `C:\AI_Projects\homeassistant\chroma_data\` | ChromaDB persistent data storage |
| `C:\AI_Projects\homeassistant\mosquitto\` | Mosquitto MQTT broker config, data, and logs |
| `C:\AI_Projects\homeassistant\esphome\` | ESPHome device configuration files |
| `C:\AI_Projects\ha_knowledge_base\chroma_db\` | ChromaDB data with ha_docs collection (37,791 docs) |
| `C:\AI_Projects\ha_knowledge_base\home-assistant.io\` | Source HA documentation repository |
| `C:\AI_Projects\ha_knowledge_base\import_ha_docs_to_chromadb.py` | Script for importing HA docs to ChromaDB |

## 12. Known Issues & Troubleshooting Guide

### Issue 1: Ollama Container Shows "Unhealthy" Status

**Symptom:** `docker ps` shows the `ollama` container as `Up X hours (unhealthy)`.

**Root Cause:** The healthcheck in `docker-compose.yml` uses `curl` to poll `http://localhost:11434/api/tags`. The `ollama/ollama:latest` image does not include `curl` by default, causing the healthcheck to fail even when the service is fully operational.

**Impact:** Cosmetic only. The Ollama API is fully functional and serves requests normally. Home Assistant and the Home Agent integration are unaffected.

**Permanent Fix:** Modify the healthcheck in `docker-compose.yml` to use a tool that is available inside the container. The recommended approach is to use `wget` or a native shell check:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -q -O - http://localhost:11434/api/tags || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

After editing the file, apply the change with:
```powershell
cd C:\AI_Projects\homeassistant
docker compose up -d --no-deps ollama
```

### Issue 2: Ollama Connection Fails After Network Change

**Symptom:** Home Agent integration fails to initialize. Error logs in Home Assistant show a connection refused or timeout error pointing to a Windows IP address (e.g., `192.168.68.73:11434`).

**Root Cause:** The LLM Base URL in the Home Agent configuration was set to the Windows host's IP address instead of the Docker container hostname. When the Windows IP changes (e.g., after a router reboot or DHCP lease renewal), the connection breaks.

**Resolution (Applied):** The LLM Base URL was changed from `http://192.168.68.73:11434/v1` to `http://ollama:11434/v1`. Because both `homeassistant` and `ollama` containers are on the same `ha_network` Docker bridge network, the container name `ollama` resolves correctly and is immune to IP changes.

**Prevention:** Always use Docker container names for inter-container communication. Never use Windows host IP addresses for services running inside Docker containers.

### Issue 3: Windows Ollama Instance Conflicts with Docker Ollama

**Symptom:** The Docker `ollama` container fails to start or bind to port 11434 because the Windows-native Ollama application is already running and occupying the port.

**Root Cause:** Ollama was configured to start automatically on Windows login via a shortcut in the Windows Startup folder (`shell:startup`).

**Resolution (Applied):** The `Ollama.lnk` shortcut was removed from `C:\Users\malon\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`. The Windows Ollama application no longer starts automatically, leaving port 11434 free for the Docker container.

### Issue 4: Aircon Container Exited

**Symptom:** The `aircon` container (image: `deiger/aircon`) shows `Exited (137) 3 days ago`.

**Root Cause:** Exit code 137 typically means the container was killed by an out-of-memory (OOM) event or was manually stopped with `docker stop`. This container is not critical to the core HA/Ollama/Voice pipeline.

**Resolution:** Investigate the container logs with `docker logs aircon` to determine the cause. If it is an OOM issue, consider adding memory limits to the `docker-compose.yml` or increasing system swap.

## 13. Maintenance & Operations

### Starting the Stack

To start all services, open PowerShell and run:
```powershell
cd C:\AI_Projects\homeassistant
docker compose up -d
```

### Stopping the Stack

```powershell
cd C:\AI_Projects\homeassistant
docker compose down
```

### Viewing Logs

To view live logs for a specific container:
```powershell
docker logs -f <container_name>
```

For example, to monitor the Ollama container:
```powershell
docker logs -f ollama
```

### Updating Containers

To pull the latest images and restart all services:
```powershell
cd C:\AI_Projects\homeassistant
docker compose pull
docker compose up -d
```

### Checking Container Health

```powershell
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

### Re-importing HA Documentation to ChromaDB

If the ChromaDB `ha_docs` collection needs to be rebuilt, run the import script:
```powershell
cd C:\AI_Projects\ha_knowledge_base
python import_ha_docs_to_chromadb.py
```

This will re-import all documents from `C:\AI_Projects\ha_knowledge_base\home-assistant.io\` into the `ha_docs` collection.

### Pulling a New Ollama Model

To pull a new model into the Ollama container:
```powershell
docker exec ollama ollama pull <model_name>
```

For example:
```powershell
docker exec ollama ollama pull llama3.1:8b-instruct-q6_K
```

---

*Document last updated: February 28, 2026*
