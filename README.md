# Freya Project

**An ongoing collection of tools, knowledge bases, and scripts for the Freya AI assistant ecosystem.**

Freya is a locally-hosted AI assistant built on Home Assistant, Ollama, and ChromaDB, running on a custom Windows 11 machine. This repository serves as the central hub for all development work related to her capabilities, knowledge, and integrations.

---

## Repository Structure

```
freya_project/
├── README.md                          ← You are here
├── SYSTEM_REFERENCE.md                ← Full system architecture reference
│
└── prompt_engineering_kb/             ← Prompt Engineering Knowledge Base
    ├── README.md                      ← KB-specific documentation
    ├── data/
    │   ├── raw_research.json          ← Raw research data (source material)
    │   └── prompt_engineering_chunks.json ← Processed, chunked documents
    └── scripts/
        ├── process_research.py        ← Chunks raw research into KB documents
        └── ingest_to_chromadb.py      ← Embeds and loads KB into ChromaDB
```

---

## System Overview

| Component | Details |
|---|---|
| **Host Machine** | FBIVAN — Windows 11 Home, 16GB RAM, RTX 5060 Ti |
| **Orchestration** | Docker Desktop + Docker Compose |
| **Core AI** | Ollama (`llama3.1:8b-instruct-q6_K`) |
| **Embeddings** | Ollama (`nomic-embed-text:latest`) |
| **Vector DB** | ChromaDB (port 8000) |
| **Smart Home Hub** | Home Assistant (port 8123) |
| **Voice Pipeline** | Wyoming Whisper (STT) + ElevenLabs (TTS) + OpenWakeWord |
| **Wake Word** | `hey_freya` |

For full system documentation, see [SYSTEM_REFERENCE.md](./SYSTEM_REFERENCE.md).

---

## Projects

### Prompt Engineering Knowledge Base

A professional-grade RAG knowledge base covering 8 major domains of prompt engineering, ingested into Freya's ChromaDB as the `prompt_engineering_kb` collection.

See [`prompt_engineering_kb/README.md`](./prompt_engineering_kb/README.md) for full details.

---

## Contributing

This is an active, ongoing project. New knowledge bases, integrations, and scripts will be added over time. Each major addition should have its own subdirectory with a `README.md` and all associated scripts.
