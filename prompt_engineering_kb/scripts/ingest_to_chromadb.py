"""
ingest_to_chromadb.py
---------------------
This script loads the processed and chunked prompt engineering knowledge base,
generates embeddings for each chunk using a local Ollama instance, and ingests
them into a ChromaDB collection.

It is designed to be run from the user's environment where it can access
the Docker-hosted Ollama and ChromaDB services.

Key Configuration:
- OLLAMA_HOST: The base URL for the Ollama API.
- EMBED_MODEL: The specific embedding model to use (must be available in Ollama).
- CHROMA_HOST: The hostname of the ChromaDB server.
- CHROMA_PORT: The port for the ChromaDB server.
- COLLECTION_NAME: The target collection for the knowledge base.
"""

import json
import os
import time
import requests
import chromadb
from tqdm import tqdm

# ── Constants & Configuration ──────────────────────────────────────────────

# --- Core Settings (match with your docker-compose.yml) ---
OLLAMA_HOST     = "http://ollama:11434"  # Use container name
EMBED_MODEL     = "nomic-embed-text:latest"
CHROMA_HOST     = "chromadb"
CHROMA_PORT     = 8000
COLLECTION_NAME = "prompt_engineering_kb"

# --- Script Paths ---
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CHUNKS_JSON = os.path.join(PROJECT_DIR, "data", "prompt_engineering_chunks.json")

# --- Batching ---
BATCH_SIZE = 50  # Number of documents to process at once

# ── Helper Functions ───────────────────────────────────────────────────────

def check_ollama_model(base_url: str, model_name: str) -> bool:
    """Check if the required embedding model is available in Ollama."""
    print(f"Verifying embedding model [33m'{model_name}'[0m is available in Ollama...")
    try:
        response = requests.get(f"{base_url}/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        for model in models:
            if model["name"] == model_name:
                print(f"[32m✓ Model found![0m")
                return True
        print(f"\n[91m[ERROR] Model '{model_name}' not found in Ollama.[0m")
        print("  Please pull the model first by running:")
        print(f"  [36mdocker exec -it ollama ollama pull {model_name}[0m\n")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n[91m[ERROR] Could not connect to Ollama at {base_url}.[0m")
        print("  Please ensure the Ollama container is running and accessible.")
        print(f"  Details: {e}")
        return False

def get_embeddings_batch(texts: list[str], base_url: str, model_name: str) -> list[list[float]] | None:
    """Get embeddings for a batch of texts from the Ollama API."""
    embeddings = []
    for text in texts:
        try:
            response = requests.post(
                f"{base_url}/api/embeddings",
                json={"model": model_name, "prompt": text}
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        except requests.exceptions.RequestException as e:
            print(f"\n[91m[ERROR] Failed to get embedding for a document.[0m")
            print(f"  Details: {e}")
            # Return what we have so far, or handle more gracefully
            return None
    return embeddings

# ── Main Ingestion Logic ───────────────────────────────────────────────────

def main():
    """Main function to run the ingestion process."""
    print("=" * 60)
    print(f"ChromaDB Knowledge Base Ingestion: {COLLECTION_NAME}")
    print("=" * 60)

    # --- 1. Load Processed Chunks ---
    if not os.path.exists(CHUNKS_JSON):
        print(f"\n[91m[ERROR] Chunks file not found: {CHUNKS_JSON}[0m")
        print("  Please run the 'process_research.py' script first.")
        return

    print(f"Loading processed chunks from [33m{CHUNKS_JSON}[0m...")
    with open(CHUNKS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    chunks = data.get("chunks", [])
    print(f"Found [32m{len(chunks)}[0m total chunks to ingest.")

    # --- 2. Verify Ollama Connection and Model ---
    if not check_ollama_model(OLLAMA_HOST, EMBED_MODEL):
        return

    # --- 3. Connect to ChromaDB ---
    print(f"\nConnecting to ChromaDB at [33m{CHROMA_HOST}:{CHROMA_PORT}[0m...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        # Check connection
        client.heartbeat()
        print("[32m✓ Successfully connected to ChromaDB.[0m")
    except Exception as e:
        print(f"\n[91m[ERROR] Could not connect to ChromaDB.[0m")
        print("  Please ensure the ChromaDB container is running and accessible.")
        print(f"  Details: {e}")
        return

    # --- 4. Get or Create Collection ---
    print(f"Accessing collection [33m'{COLLECTION_NAME}'[0m...")
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # Using cosine for semantic similarity
    )
    print("[32m✓ Collection is ready.[0m")

    # --- 5. Ingest Documents in Batches ---
    print(f"\nStarting ingestion in batches of {BATCH_SIZE}...")
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Ingesting Batches", unit="batch"):
        batch = chunks[i:i + BATCH_SIZE]

        ids      = [item["id"] for item in batch]
        docs     = [item["document"] for item in batch]
        metadata = [item["metadata"] for item in batch]

        # Generate embeddings for the batch
        embeddings = get_embeddings_batch(docs, OLLAMA_HOST, EMBED_MODEL)

        if embeddings is None or len(embeddings) != len(batch):
            print("\n[91m[FATAL] Embedding generation failed. Aborting ingestion.[0m")
            return

        # Add the batch to ChromaDB
        try:
            collection.add(
                ids=ids,
                documents=docs,
                metadatas=metadata,
                embeddings=embeddings
            )
        except Exception as e:
            print(f"\n[91m[ERROR] Failed to add batch {i // BATCH_SIZE + 1} to ChromaDB.[0m")
            print(f"  Details: {e}")
            # Optional: decide whether to continue or stop
            # For now, we stop to avoid partial ingestion
            return

    print("\n" + "=" * 60)
    print("[32m✓ Ingestion Complete![0m")
    print("=" * 60)
    final_count = collection.count()
    print(f"The [33m'{COLLECTION_NAME}'[0m collection now contains [32m{final_count}[0m documents.")
    print("You can now query this knowledge base with your RAG application.")

if __name__ == "__main__":
    # Add a requirements check for user convenience
    try:
        import requests
        import chromadb
        from tqdm import tqdm
    except ImportError:
        print("\n[91m[ERROR] Missing required Python packages.[0m")
        print("  Please install them by running:")
        print("  [36mpip install requests chromadb tqdm[0m\n")
    else:
        main()
