# Freya Knowledge Bases

This directory is the central home for all ChromaDB knowledge bases used by Freya. Each knowledge base lives in its own subdirectory with a consistent structure.

---

## Directory Structure

```
knowledge_bases/
├── README.md                              ← This file
├── setup_knowledge_bases.ps1             ← One-time setup/organization script
├── freya_system_prompt.txt               ← Updated system prompt (paste into Home Agent)
│
├── ha_docs/
│   └── scripts/
│       └── import_ha_docs_to_chromadb.py ← Re-import HA documentation
│
├── google_dorking_knowledge/
│   └── scripts/
│       └── import_google_dorking.py      ← Re-import dorking techniques
│
└── prompt_engineering_kb/
    ├── scripts/
    │   ├── ingest_to_chromadb.py         ← Embed & load into ChromaDB
    │   └── process_research.py           ← Re-chunk raw research data
    └── data/
        ├── prompt_engineering_chunks.json ← 151 processed chunks (ready to ingest)
        └── raw_research.json             ← Source research material
```

---

## ChromaDB Collections Summary

| Collection | Docs | Description |
|---|---|---|
| `ha_docs` | 37,791 | Home Assistant documentation |
| `home_entities` | varies | Tomie's smart home devices and entity IDs |
| `google_dorking_knowledge` | varies | Google search operators and OSINT techniques |
| `prompt_engineering_kb` | 151 | Pro-level prompt engineering techniques |

---

## First-Time Setup

**Step 1 — Run the setup script** to organize all files into the right places:

```powershell
cd C:\AI_Projects\homeassistant
.\knowledge_bases\setup_knowledge_bases.ps1
```

**Step 2 — Ingest the Prompt Engineering KB** (the only new one that needs loading):

```powershell
# Install dependencies if needed
pip install requests chromadb tqdm

python knowledge_bases\prompt_engineering_kb\scripts\ingest_to_chromadb.py
```

**Step 3 — Update Freya's system prompt** in Home Assistant:

- Open `knowledge_bases\freya_system_prompt.txt`
- Copy the entire contents
- In HA: **Settings → Voice Assistants → Freya → Home Agent → System Prompt**
- Paste and save

---

## Re-Ingesting a Knowledge Base

If you ever need to rebuild a collection from scratch (e.g., after a ChromaDB reset):

```powershell
# HA Docs
python knowledge_bases\ha_docs\scripts\import_ha_docs_to_chromadb.py

# Google Dorking
python knowledge_bases\google_dorking_knowledge\scripts\import_google_dorking.py

# Prompt Engineering
python knowledge_bases\prompt_engineering_kb\scripts\ingest_to_chromadb.py
```

---

## Adding a New Knowledge Base

1. Create a new subdirectory: `knowledge_bases\<collection_name>\`
2. Add `scripts\` and `data\` subdirectories
3. Write an ingestion script following the pattern in `prompt_engineering_kb\scripts\ingest_to_chromadb.py`
4. Add the new collection to the table in `freya_system_prompt.txt`
5. Update this README
