"""
import_ha_entities_to_chromadb.py

Pulls all entities from Home Assistant via the REST API, enriches them with
semantic context (domain, friendly name, location hints, state), and imports
them into the ChromaDB `home_entities` collection.

Also purges any stale entity/device references from Freya's memory collections
(freya_facts and freya_memories) so she stops hallucinating old or renamed
entity IDs.

Run this script on the Windows host machine (where Docker is running).

Requirements:
    pip install chromadb requests

Usage:
    python import_ha_entities_to_chromadb.py
"""

import hashlib
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these values if needed
# ---------------------------------------------------------------------------
CONFIG = {
    # Home Assistant base URL (from the host machine)
    "ha_url": "http://localhost:8123",

    # Long-Lived Access Token from your HA profile page
    "ha_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4MjcxYzMzM2Q1NTk0ODA1YjQ1YTQxM2U1ZjEwOTJlNSIsImlhdCI6MTc3MjQzMzUwMywiZXhwIjoyMDg3NzkzNTAzfQ.cxWfPAjDx2d9D_GNO_RjDtqjir2giySVPydz6Miwj0Q",

    # ChromaDB HTTP server (Docker container exposed on host)
    "chroma_host": "localhost",
    "chroma_port": 8000,

    # Collection to populate with live HA entities
    "collection_name": "home_entities",

    # Freya memory collections to clean stale entity references from
    "freya_facts_collection": "freya_facts",
    "freya_memories_collection": "freya_memories",

    # Domains to EXCLUDE (noisy internal HA entities not useful for Freya)
    "exclude_domains": {
        "persistent_notification",
        "conversation",
        "tts",
        "stt",
        "wake_word",
        "assist_pipeline",
        "update",
        "event",
    },

    # Batch size for ChromaDB upserts
    "batch_size": 50,
}
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ha_import")


# ---------------------------------------------------------------------------
# Domain metadata — human-readable descriptions for each HA domain
# ---------------------------------------------------------------------------
DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "light": "smart light or lamp",
    "switch": "smart switch or plug",
    "binary_sensor": "binary sensor (on/off detector)",
    "sensor": "sensor (temperature, humidity, power, etc.)",
    "climate": "thermostat or climate control device",
    "media_player": "media player (TV, speaker, streaming device)",
    "camera": "security camera or video feed",
    "cover": "cover (blinds, garage door, curtains)",
    "lock": "smart lock",
    "alarm_control_panel": "alarm or security panel",
    "fan": "smart fan",
    "vacuum": "robot vacuum",
    "input_boolean": "manual toggle helper",
    "input_number": "numeric input helper",
    "input_select": "dropdown selector helper",
    "input_text": "text input helper",
    "input_datetime": "date/time input helper",
    "automation": "automation rule",
    "script": "HA script",
    "scene": "scene (preset group state)",
    "person": "tracked person",
    "device_tracker": "device location tracker",
    "weather": "weather service",
    "sun": "sun position sensor",
    "zone": "geographic zone",
    "timer": "countdown timer",
    "counter": "counter helper",
    "number": "numeric entity",
    "select": "select entity",
    "button": "button entity",
    "text": "text entity",
    "todo": "to-do list",
    "calendar": "calendar",
    "image": "image entity",
    "remote": "remote control",
    "siren": "siren or alarm",
    "water_heater": "water heater",
    "humidifier": "humidifier or dehumidifier",
    "lawn_mower": "robotic lawn mower",
}

# Keywords in memory content that suggest the entry is about a device/entity
ENTITY_MEMORY_KEYWORDS = [
    "entity_id", "light.", "switch.", "sensor.", "binary_sensor.", "climate.",
    "media_player.", "camera.", "cover.", "lock.", "fan.", "vacuum.", "scene.",
    "script.", "automation.", "input_boolean.", "input_number.", "input_select.",
    "device", "entity", "smart plug", "smart light", "lamp", "bulb", "thermostat",
    "camera feed", "motion sensor", "door sensor", "window sensor",
]


def get_domain(entity_id: str) -> str:
    return entity_id.split(".")[0]


def get_object_id(entity_id: str) -> str:
    return entity_id.split(".", 1)[1] if "." in entity_id else entity_id


def humanize_object_id(object_id: str) -> str:
    return object_id.replace("_", " ").strip()


def infer_location(friendly_name: str, object_id: str) -> str:
    location_keywords = [
        "living room", "bedroom", "master bedroom", "guest bedroom",
        "kitchen", "bathroom", "garage", "office", "study", "basement",
        "attic", "hallway", "entryway", "foyer", "dining room", "laundry",
        "porch", "patio", "backyard", "front yard", "driveway", "mudroom",
        "nursery", "playroom", "gym", "theater", "media room", "sunroom",
        "utility room", "pantry", "closet", "stairway", "loft",
        "outside", "outdoor", "exterior", "indoor", "interior",
    ]
    combined = (friendly_name + " " + humanize_object_id(object_id)).lower()
    for loc in location_keywords:
        if loc in combined:
            return loc.title()
    return "Unknown"


def build_document(entity: dict[str, Any]) -> str:
    entity_id: str = entity.get("entity_id", "")
    state: str = str(entity.get("state", "unknown"))
    attributes: dict = entity.get("attributes", {})

    domain = get_domain(entity_id)
    object_id = get_object_id(entity_id)
    friendly_name: str = attributes.get("friendly_name") or humanize_object_id(object_id)
    domain_desc = DOMAIN_DESCRIPTIONS.get(domain, f"{domain} entity")
    location = infer_location(friendly_name, object_id)

    detail_parts: list[str] = []

    device_class = attributes.get("device_class")
    if device_class:
        detail_parts.append(f"device class: {device_class}")

    unit = attributes.get("unit_of_measurement")
    if unit:
        detail_parts.append(f"unit: {unit}")

    supported_color_modes = attributes.get("supported_color_modes", [])
    if supported_color_modes:
        detail_parts.append(f"color modes: {', '.join(supported_color_modes)}")

    media_content_type = attributes.get("media_content_type")
    if media_content_type:
        detail_parts.append(f"media type: {media_content_type}")

    hvac_modes = attributes.get("hvac_modes")
    if hvac_modes:
        detail_parts.append(f"HVAC modes: {', '.join(hvac_modes)}")

    source_list = attributes.get("source_list")
    if source_list and isinstance(source_list, list):
        detail_parts.append(f"sources: {', '.join(str(s) for s in source_list[:5])}")

    details_str = ("; " + "; ".join(detail_parts)) if detail_parts else ""

    return (
        f"Entity: {entity_id}\n"
        f"Friendly Name: {friendly_name}\n"
        f"Type: {domain_desc}\n"
        f"Location: {location}\n"
        f"Current State: {state}{details_str}\n"
        f"Domain: {domain}\n"
        f"Object ID: {object_id}"
    )


def stable_id(entity_id: str) -> str:
    return hashlib.md5(entity_id.encode()).hexdigest()


def fetch_entities(ha_url: str, token: str) -> list[dict]:
    url = f"{ha_url.rstrip('/')}/api/states"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    log.info(f"Fetching entities from {url} ...")
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        log.error(
            f"Cannot connect to Home Assistant at {ha_url}. "
            "Make sure HA is running and the URL is correct."
        )
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP error from HA API: {e}")
        sys.exit(1)

    entities = resp.json()
    log.info(f"Fetched {len(entities)} total entities from Home Assistant.")
    return entities


def filter_entities(entities: list[dict], exclude_domains: set[str]) -> list[dict]:
    filtered = [
        e for e in entities
        if get_domain(e.get("entity_id", "")) not in exclude_domains
        and not e.get("entity_id", "").startswith("_")
    ]
    log.info(
        f"After filtering excluded domains: {len(filtered)} entities remain "
        f"({len(entities) - len(filtered)} excluded)."
    )
    return filtered


def purge_stale_entity_memories(
    client: Any,
    valid_entity_ids: set[str],
    facts_collection_name: str,
    memories_collection_name: str,
) -> None:
    """
    Remove stale entity/device references from Freya's memory collections.

    Strategy:
    - freya_facts: delete any entry whose metadata category is 'entity' or
      'device', OR whose stored value contains an entity_id that no longer
      exists in HA.
    - freya_memories: delete any entry whose content references an entity_id
      that no longer exists in HA.

    Personal memories (name, birthday, preferences, etc.) are NOT touched.
    """
    log.info("-" * 50)
    log.info("Checking for stale entity references in Freya's memory...")

    # --- freya_facts ---
    try:
        facts_col = client.get_collection(name=facts_collection_name)
    except Exception:
        log.info(f"  Collection '{facts_collection_name}' not found — skipping.")
        facts_col = None

    if facts_col and facts_col.count() > 0:
        all_facts = facts_col.get(include=["metadatas", "documents"])
        stale_fact_ids = []

        for doc_id, meta, doc in zip(
            all_facts["ids"], all_facts["metadatas"], all_facts["documents"]
        ):
            category = (meta or {}).get("category", "")
            value = (meta or {}).get("value", "")
            doc_text = doc or ""

            # Delete if category is device/entity related
            if category.lower() in {"entity", "device", "entity_id", "home_entity"}:
                stale_fact_ids.append(doc_id)
                continue

            # Delete if the stored value looks like an entity_id that no longer exists
            if "." in value and value in {e for e in valid_entity_ids}:
                # It's a valid entity — keep it
                continue
            if "." in value and any(
                value.startswith(f"{domain}.") for domain in DOMAIN_DESCRIPTIONS
            ):
                # Looks like an entity_id but isn't in the live list — stale
                stale_fact_ids.append(doc_id)
                continue

        if stale_fact_ids:
            facts_col.delete(ids=stale_fact_ids)
            log.info(f"  Removed {len(stale_fact_ids)} stale entity facts from '{facts_collection_name}'.")
        else:
            log.info(f"  No stale entity facts found in '{facts_collection_name}'.")

    # --- freya_memories ---
    try:
        mem_col = client.get_collection(name=memories_collection_name)
    except Exception:
        log.info(f"  Collection '{memories_collection_name}' not found — skipping.")
        mem_col = None

    if mem_col and mem_col.count() > 0:
        all_mems = mem_col.get(include=["documents", "metadatas"])
        stale_mem_ids = []

        for doc_id, doc, meta in zip(
            all_mems["ids"], all_mems["documents"], all_mems["metadatas"]
        ):
            doc_text = (doc or "").lower()

            # Only consider memories that mention entity-like content
            if not any(kw in doc_text for kw in ENTITY_MEMORY_KEYWORDS):
                continue

            # Check if the memory references a specific entity_id that no longer exists
            for word in doc_text.split():
                word = word.strip(".,;:\"'()")
                if "." in word and any(
                    word.startswith(f"{domain}.") for domain in DOMAIN_DESCRIPTIONS
                ):
                    if word not in valid_entity_ids:
                        stale_mem_ids.append(doc_id)
                        break

        if stale_mem_ids:
            mem_col.delete(ids=stale_mem_ids)
            log.info(
                f"  Removed {len(stale_mem_ids)} stale entity memories from '{memories_collection_name}'."
            )
        else:
            log.info(f"  No stale entity memories found in '{memories_collection_name}'.")

    log.info("Memory cleanup complete.")
    log.info("-" * 50)


def import_to_chromadb(
    entities: list[dict],
    chroma_host: str,
    chroma_port: int,
    collection_name: str,
    facts_collection_name: str,
    memories_collection_name: str,
    batch_size: int,
) -> None:
    try:
        import chromadb
    except ImportError:
        log.error("chromadb package not found. Run: pip install chromadb")
        sys.exit(1)

    log.info(f"Connecting to ChromaDB at {chroma_host}:{chroma_port} ...")
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    try:
        client.heartbeat()
        log.info("ChromaDB connection successful.")
    except Exception as e:
        log.error(f"Cannot connect to ChromaDB: {e}")
        sys.exit(1)

    # Build the set of valid (live) entity IDs for use in cleanup
    valid_entity_ids: set[str] = {e["entity_id"] for e in entities if "entity_id" in e}

    # --- Step 1: Purge stale entity memories ---
    purge_stale_entity_memories(
        client=client,
        valid_entity_ids=valid_entity_ids,
        facts_collection_name=facts_collection_name,
        memories_collection_name=memories_collection_name,
    )

    # --- Step 2: Upsert live entities into home_entities ---
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Home Assistant entity knowledge base for Freya"},
    )

    existing_count = collection.count()
    log.info(
        f"Collection '{collection_name}' has {existing_count} existing documents. "
        "Upserting all current entities..."
    )

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for entity in entities:
        entity_id: str = entity.get("entity_id", "")
        attributes: dict = entity.get("attributes", {})
        domain = get_domain(entity_id)
        friendly_name: str = (
            attributes.get("friendly_name") or humanize_object_id(get_object_id(entity_id))
        )

        ids.append(stable_id(entity_id))
        documents.append(build_document(entity))
        metadatas.append({
            "entity_id": entity_id,
            "domain": domain,
            "friendly_name": friendly_name,
            "state": str(entity.get("state", "unknown")),
            "location": infer_location(friendly_name, get_object_id(entity_id)),
            "last_updated": now_iso,
        })

    total = len(ids)
    upserted = 0
    for i in range(0, total, batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_docs = documents[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]

        collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_meta,
        )
        upserted += len(batch_ids)
        log.info(f"  Upserted {upserted}/{total} entities...")
        time.sleep(0.1)

    final_count = collection.count()
    log.info(
        f"\n✅ Import complete!\n"
        f"   Collection      : {collection_name}\n"
        f"   Total documents : {final_count}\n"
        f"   Timestamp       : {now_iso}"
    )


def main() -> None:
    log.info("=" * 60)
    log.info("  Home Assistant → ChromaDB Entity Importer")
    log.info("  (includes stale memory cleanup)")
    log.info("=" * 60)

    entities = fetch_entities(CONFIG["ha_url"], CONFIG["ha_token"])
    entities = filter_entities(entities, CONFIG["exclude_domains"])

    if not entities:
        log.warning("No entities to import after filtering. Exiting.")
        sys.exit(0)

    import_to_chromadb(
        entities=entities,
        chroma_host=CONFIG["chroma_host"],
        chroma_port=CONFIG["chroma_port"],
        collection_name=CONFIG["collection_name"],
        facts_collection_name=CONFIG["freya_facts_collection"],
        memories_collection_name=CONFIG["freya_memories_collection"],
        batch_size=CONFIG["batch_size"],
    )


if __name__ == "__main__":
    main()
