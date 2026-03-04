"""
build_home_entities.py
======================
Reads ha_entities_export.json (exported from HA API), filters to actionable
entities, builds rich semantic documents, and ingests them into ChromaDB
collection 'home_entities' using nomic-embed-text via Ollama.

Usage:
    python build_home_entities.py

Requirements:
    pip install requests chromadb tqdm

Settings (edit below to match your environment):
"""

import json
import uuid
import requests
from tqdm import tqdm

# --- Settings ---
ENTITIES_FILE   = r"C:\AI_Projects\homeassistant\ha_entities_export.json"
OLLAMA_HOST     = "http://localhost:11434"
EMBED_MODEL     = "nomic-embed-text:latest"
CHROMA_HOST     = "localhost"
CHROMA_PORT     = 8000
COLLECTION_NAME = "home_entities"

# Domains to include in the knowledge base
INCLUDE_DOMAINS = {
    "light", "switch", "cover", "camera", "media_player", "climate",
    "fan", "lock", "alarm_control_panel", "scene", "script", "automation",
    "button", "binary_sensor", "sensor", "input_boolean", "number",
    "select", "siren", "vacuum", "humidifier", "input_select",
    "input_number", "input_text", "timer", "counter"
}

# Domains to skip (internal/system/noisy)
SKIP_DOMAINS = {
    "conversation", "tts", "stt", "wake_word", "update", "person",
    "zone", "sun", "weather", "persistent_notification", "event",
    "device_tracker"
}

# Sensor sub-types to skip (too noisy / not useful for voice control)
SKIP_SENSOR_KEYWORDS = [
    "moon_astro", "electricity_maps", "backup_", "sun_next",
    "geocoded_location", "bssid", "ssid", "sim_1", "sim_2",
    "app_version", "last_update_trigger", "location_permission",
    "ecliptic", "parallax", "apogee", "perigee"
]


def load_entities(path):
    """Load entities from HA export file (handles UTF-16 from PowerShell)."""
    try:
        with open(path, "r", encoding="utf-16") as f:
            data = json.load(f)
        # PowerShell wraps the array in {"value": [...], "Count": N}
        if isinstance(data, dict) and "value" in data:
            return data["value"]
        return data
    except UnicodeDecodeError:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "value" in data:
            return data["value"]
        return data


def should_include(entity):
    """Return True if this entity is worth indexing."""
    entity_id = entity["entity_id"]
    domain = entity_id.split(".")[0]

    if domain in SKIP_DOMAINS:
        return False
    if domain not in INCLUDE_DOMAINS:
        return False

    # Skip noisy sensor sub-types
    if domain == "sensor":
        for kw in SKIP_SENSOR_KEYWORDS:
            if kw in entity_id:
                return False

    return True


def infer_location(entity_id, friendly_name):
    """Best-effort room/location inference from entity name."""
    name_lower = (entity_id + " " + friendly_name).lower()
    location_map = {
        "living room": ["living", "lounge", "couch", "sofa", "tv", "television"],
        "bedroom": ["bedroom", "bed", "sleep"],
        "kitchen": ["kitchen", "counter", "stove", "fridge"],
        "bathroom": ["bathroom", "bath", "shower", "toilet"],
        "office": ["office", "desk", "computer", "pc", "war room", "warroom"],
        "front door": ["front door", "porch", "entrance", "driveway", "front"],
        "garage": ["garage"],
        "backyard": ["backyard", "back yard", "outdoor", "outside"],
        "whole home": ["all", "scene", "global"],
    }
    for location, keywords in location_map.items():
        for kw in keywords:
            if kw in name_lower:
                return location
    return "unknown"


def build_document(entity):
    """Build a rich semantic text document for a single entity."""
    entity_id    = entity["entity_id"]
    domain       = entity_id.split(".")[0]
    attrs        = entity.get("attributes", {})
    friendly     = attrs.get("friendly_name", entity_id)
    state        = entity.get("state", "unknown")
    device_class = attrs.get("device_class", "")
    unit         = attrs.get("unit_of_measurement", "")
    location     = infer_location(entity_id, friendly)

    # Build aliases list for better semantic matching
    aliases = [friendly]
    # Add cleaned-up name variants
    clean = friendly.lower().replace("_", " ").replace("-", " ")
    if clean not in [a.lower() for a in aliases]:
        aliases.append(clean)

    doc_parts = [
        f"Entity: {friendly}",
        f"Entity ID: {entity_id}",
        f"Domain: {domain}",
        f"Location: {location}",
        f"Current state: {state}",
    ]
    if device_class:
        doc_parts.append(f"Device class: {device_class}")
    if unit:
        doc_parts.append(f"Unit: {unit}")
    if len(aliases) > 1:
        doc_parts.append(f"Also known as: {', '.join(aliases)}")

    # Domain-specific context
    if domain == "light":
        brightness = attrs.get("brightness")
        color_temp = attrs.get("color_temp")
        if brightness:
            doc_parts.append(f"Brightness: {round(brightness / 255 * 100)}%")
        if color_temp:
            doc_parts.append(f"Color temp: {color_temp}")
        doc_parts.append("This is a controllable light. Can be turned on, off, dimmed, or color-adjusted.")
    elif domain == "switch":
        doc_parts.append("This is a controllable switch. Can be turned on or off.")
    elif domain == "cover":
        doc_parts.append("This is a cover (blind, shade, or motorized surface). Can be opened, closed, or stopped.")
    elif domain == "camera":
        doc_parts.append("This is a camera. Can show a live feed or snapshot.")
    elif domain == "media_player":
        doc_parts.append("This is a media player. Can play, pause, stop, change volume, or change source.")
    elif domain == "climate":
        doc_parts.append("This is a climate/thermostat device. Can set temperature, mode, or fan speed.")
    elif domain == "scene":
        doc_parts.append("This is a scene. Activating it sets multiple devices to predefined states simultaneously.")
    elif domain == "script":
        doc_parts.append("This is a script. Running it executes a sequence of HA actions.")
    elif domain == "automation":
        doc_parts.append("This is an automation. It can be triggered, enabled, or disabled.")
    elif domain == "binary_sensor":
        doc_parts.append(f"This is a binary sensor. Reports on/off, open/closed, or detected/clear states.")
    elif domain == "sensor":
        doc_parts.append(f"This is a sensor that reports a measurement or status value.")
    elif domain == "input_boolean":
        doc_parts.append("This is a toggle helper. Can be turned on or off.")
    elif domain == "lock":
        doc_parts.append("This is a lock. Can be locked or unlocked.")
    elif domain == "fan":
        doc_parts.append("This is a fan. Can be turned on, off, or speed-adjusted.")

    return "\n".join(doc_parts), {
        "entity_id":    entity_id,
        "friendly_name": friendly,
        "domain":       domain,
        "location":     location,
        "state":        state,
        "device_class": device_class,
    }


def get_embedding(text):
    """Get embedding from Ollama."""
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def main():
    print("\n=== Freya Home Entities Ingestion ===\n")

    # 1. Load entities
    print(f"Loading entities from {ENTITIES_FILE}...")
    all_entities = load_entities(ENTITIES_FILE)
    print(f"  Total in export: {len(all_entities)}")

    # 2. Filter
    filtered = [e for e in all_entities if should_include(e)]
    print(f"  After filtering: {len(filtered)} actionable entities\n")

    # 3. Verify Ollama
    print(f"Verifying Ollama model '{EMBED_MODEL}'...")
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(EMBED_MODEL.split(":")[0] in m for m in models):
            print(f"  WARNING: {EMBED_MODEL} not found. Available: {models}")
        else:
            print(f"  OK - model found")
    except Exception as ex:
        print(f"  ERROR connecting to Ollama: {ex}")
        return

    # 4. Connect to ChromaDB
    print(f"\nConnecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
    import chromadb
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    # Delete existing collection and recreate fresh
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing '{COLLECTION_NAME}' collection")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"  Collection '{COLLECTION_NAME}' ready\n")

    # 5. Embed and ingest
    print(f"Embedding and ingesting {len(filtered)} entities...")
    ids, embeddings, documents, metadatas = [], [], [], []

    for entity in tqdm(filtered, desc="Embedding"):
        doc_text, metadata = build_document(entity)
        try:
            embedding = get_embedding(doc_text)
        except Exception as ex:
            print(f"\n  SKIP {entity['entity_id']}: {ex}")
            continue

        ids.append(str(uuid.uuid4()))
        embeddings.append(embedding)
        documents.append(doc_text)
        metadatas.append(metadata)

    # Batch upsert
    BATCH = 50
    for i in range(0, len(ids), BATCH):
        collection.upsert(
            ids=ids[i:i+BATCH],
            embeddings=embeddings[i:i+BATCH],
            documents=documents[i:i+BATCH],
            metadatas=metadatas[i:i+BATCH],
        )

    final_count = collection.count()
    print(f"\n=================================================")
    print(f"  '{COLLECTION_NAME}' now contains {final_count} documents.")
    print(f"  Freya can now resolve device references semantically.")
    print(f"=================================================\n")


if __name__ == "__main__":
    main()
