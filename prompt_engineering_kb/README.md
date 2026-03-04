# Prompt Engineering Knowledge Base

A professional-grade, RAG-ready knowledge base covering pro-level prompt engineering techniques. Designed to be ingested into Freya's ChromaDB so she can answer questions about prompting strategies with deep, authoritative knowledge.

---

## Knowledge Base Contents

The knowledge base covers **151 semantic chunks** across **8 expert-level domains**:

| Category | Collection Slug | Chunks | Description |
|---|---|---|---|
| Reasoning Techniques | `reasoning_techniques` | 15 | CoT, Zero-shot CoT, Tree of Thought, Self-Consistency |
| In-Context Learning | `in_context_learning` | 18 | Few-shot, Zero-shot, example selection, label calibration |
| Agentic Prompting | `agentic_prompting` | 41 | ReAct, Reflexion, tool-use, multi-step agent workflows |
| Prompt Optimization | `prompt_optimization` | 14 | OPRO, APE, DSPy, automatic prompt engineering |
| RAG & Retrieval | `rag_and_retrieval` | 16 | Query construction, context injection, chunking strategies |
| System Prompt Engineering | `system_prompt_engineering` | 13 | Persona design, constraint setting, output format control |
| Image Generation | `image_generation` | 14 | Stable Diffusion, Midjourney, DALL-E, hyperrealism |
| Adversarial & Security | `adversarial_and_security` | 20 | Prompt injection, jailbreaking, red-teaming, defenses |

---

## ChromaDB Collection

| Setting | Value |
|---|---|
| **Collection Name** | `prompt_engineering_kb` |
| **Embedding Model** | `nomic-embed-text:latest` (via Ollama) |
| **Distance Metric** | Cosine similarity |
| **Total Documents** | 151 |

---

## How to Use

### Prerequisites

Make sure the following Docker containers are running:
- `ollama` — with `nomic-embed-text:latest` pulled
- `chromadb` — accessible on port 8000

Install Python dependencies:
```powershell
pip install requests chromadb tqdm
```

### Step 1: Process the Raw Research (optional, already done)

This step converts the raw research JSON into semantically chunked documents with metadata. Only needed if you want to re-process or add new research.

```powershell
cd C:\AI_Projects\homeassistant\freya_project
python prompt_engineering_kb\scripts\process_research.py
```

### Step 2: Ingest into ChromaDB

This is the main step. It reads the processed chunks, generates embeddings using Ollama, and loads them into ChromaDB.

**Important:** Run this script from inside the Docker network, or update `OLLAMA_HOST` and `CHROMA_HOST` in the script to use `localhost` if running from the Windows host.

**Option A — Run from Windows host (recommended for first-time setup):**

Edit `ingest_to_chromadb.py` and change:
```python
OLLAMA_HOST = "http://localhost:11434"
CHROMA_HOST = "localhost"
```

Then run:
```powershell
cd C:\AI_Projects\homeassistant\freya_project
python prompt_engineering_kb\scripts\ingest_to_chromadb.py
```

**Option B — Run from inside a Docker container:**

Keep the default container hostnames (`ollama`, `chromadb`) and run via Docker exec.

### Step 3: Verify the Collection

After ingestion, verify the collection was created:
```powershell
# Using Python
python -c "import chromadb; c = chromadb.HttpClient(host='localhost', port=8000); print(c.get_collection('prompt_engineering_kb').count())"
```

You should see `151` (or more if you've added additional documents).

---

## Adding New Knowledge

To expand the knowledge base with new topics:

1. Add new research content to `data/raw_research.json` following the existing schema.
2. Re-run `process_research.py` to regenerate `prompt_engineering_chunks.json`.
3. Re-run `ingest_to_chromadb.py`. The script uses `get_or_create_collection` and `add`, so it will append new documents without duplicating existing ones (IDs are deterministic hashes).

---

## Querying from Home Assistant / Freya

Once ingested, Freya can query this collection via the Home Agent integration's ChromaDB connection. The collection name to use in queries is:

```
prompt_engineering_kb
```

Example semantic query: *"What is the best prompting technique for multi-step reasoning tasks?"*

---

## File Reference

| File | Description |
|---|---|
| `data/raw_research.json` | Source research data from the parallel research phase |
| `data/prompt_engineering_chunks.json` | Processed, chunked, metadata-enriched documents ready for ingestion |
| `scripts/process_research.py` | Splits raw markdown research into semantic chunks with metadata |
| `scripts/ingest_to_chromadb.py` | Generates embeddings via Ollama and loads documents into ChromaDB |
