# 🟣 FREYA — Local AI Voice Assistant
*A fully local, multi-channel, wake-word-activated AI assistant powered by Whisper + Ollama + Piper.*

Freya is a modular, privacy-first voice assistant that runs **100% offline** on your PC.  
It uses:

- **Lightweight Whisper** for wake-word detection  
- **Full Whisper model** for command transcription  
- **Ollama (Dolphin 3, etc.)** for LLM responses  
- **Piper TTS** for fast, natural speech  
- **Independent audio channels** (e.g., front door mic + bedroom mic)  
- **Modular design** you can expand with new features

---

## 🚀 Features

### 🎤 **Dual-stage STT**
- **Stage 1:** Ultra-light Whisper model running *constantly* for wake word detection  
- **Stage 2:** After activation, full Whisper listens for **8 seconds** for your command  

### 🔊 **Independent Audio Channels**
Freya can handle multiple mics/speakers at once:
- Bedroom mic → Bedroom speaker  
- Front door mic → Front door speaker  
- Esp32/Reolink camera streams  
Each runs **asynchronously** with its own logic.

### 🧠 **Local LLM (Ollama)**
Supports any installed model:
- dolphin3:8b  
- mistral  
- llama3  
- deepseek  

You can swap models in config.

### 🗣️ **Fast Local TTS (Piper)**
Output is low-latency, natural-sounding voice using your installed `.onnx` model.

### 👁️ **Facial Recognition Module**
Optional add-on (`freya/facial_recognition.py`) for:
- Identifying known faces  
- Triggering personalized responses  
- Supporting Reolink RTSP streams  

### 🔧 **Modular Architecture**
```
freya/
│── audio_config.py
│── config.py
│── context.py
│── facial_recognition.py
│── logger.py
│── memory.py
│── multi_channel_coordinator.py
│── ollama_client.py
│── orchestrator.py
│── stt.py
│── system_check.py
│── tts.py
│── wake.py
│── tools/
│      └── web_search.py
```

### 🧠 **Short-Term + Long-Term Memory**
Memory is stored locally in `data/freya_memory.db`.

### 🔍 **Optional Web Search (DuckDuckGo)**
Uses local tool wrapper under:  
`freya/tools/web_search.py`

### 🧪 **Test Suite Included**
Under `/tests/`:
- audio tests  
- memory tests  
- mic tests  
- wake-word tests  
- facial recognition tests  

---

## 📁 Project Structure

```
freya_project/
│── config/
│   └── default.yaml
│── data/
│   └── freya_memory.db
│── docs/
│   ├── multi_channel_overview.md
│   ├── readme.md
│   └── readme2.md
│── freya/
│   ├── ... (core modules)
│── main.py
│── requirements.txt
│── tests/
│   ├── test_audio_config.py
│   ├── test_facial_recognition.py
│   ├── test_memory.py
│   └── ...
└── voices/
    └── en_US-lessac-medium.onnx.json
```

---

## ⚙️ Installation

### **1. Clone your repo**
```bash
git clone https://github.com/MrPink1977/freya_project.git
cd freya_project
```

### **2. Create a virtual env**
```bash
python -m venv freya_env
freya_env\Scripts\activate
```

### **3. Install dependencies**
```bash
pip install -r requirements.txt
```

### **4. Install Whisper + FFmpeg**
You already have these installed locally — but on a new system:

- Install FFmpeg  
- Install faster-whisper  
- Install piper

---

## 🟢 Running Freya

```bash
python main.py
```

Once running:

- Whisper listens lightly for wake word (default: **"freya"**)  
- When detected → full STT runs for 8 seconds  
- Your command is sent to Ollama  
- Piper replies through the correct speaker  
- System returns to wake-word listening

---

## 🛠️ Configuration

Settings are stored in:

```
config/default.yaml
```

Editable fields:
- Wake word(s)
- Whisper model paths
- Audio devices
- TTS voice model
- Ollama model
- Memory depth
- Reolink camera URLs
- Multi-channel behavior

---

## 📡 Multi-Channel System

Documentation here:

`docs/multi_channel_overview.md`

Shows how Freya:

- Handles multiple microphones  
- Assigns each channel an audio pipeline  
- Prevents cross-talk / feedback  
- Routes responses to the correct output  

---

## 🔐 Privacy

Freya:

- Sends **zero** data to the cloud  
- Runs completely offline  
- Stores memory locally  
- Uses your own GPU for STT + LLM + TTS  

---

## 🧩 Extend Freya

Add your own modules under:

```
freya/tools/
```

Examples:
- smart lights  
- home security  
- weather  
- LLM agents  
- automation  

---

## 🤝 Contributing

PRs welcome.  
Issues welcome.  
Forks welcome.

---

## 📜 License

MIT License  
(We can generate the file if you want.)

---
