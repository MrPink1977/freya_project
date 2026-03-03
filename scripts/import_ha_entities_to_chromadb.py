"""
import_ha_entities_to_chromadb.py

Pulls all entities from Home Assistant via the REST API, enriches them with
semantic context (domain, friendly name, location hints, state), and imports
them into the ChromaDB `home_entities` collection.

Run this script on the Windows host machine (where Docker is running).

Requirements:
    pip install chromadb requests

Usage:
    python import_ha_entities_to_chromadb.py

Configuration:
    Edit the CONFIG block below before running.
"""

import hashlib
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these values before running
# ---------------------------------------------------------------------------
CONFIG = {
    # Home Assistant base URL (from the host machine)
    "ha_url": "http://localhost:8123",

    # Long-Lived Access Token from your HA profile page
    "ha_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4MjcxYzMzM2Q1NTk0ODA1YjQ1YTQxM2U1ZjEwOTJlNSIsImlhdCI6MTc3MjQzMzUwMywiZXhwIjoyMDg3NzkzNTAzfQ.cxWfPAjDx2d9D_GNO_RjDtqjir2giySVPydz6Miwj0Q",

    # ChromaDB HTTP server (Docker container exposed on host)
    "chroma_host": "localhost",
    "chroma_port": 8000,

    # Collection name to populate
    "collection_name": "home_entities",

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


def get_domain(entity_id: str) -> str:
    """Extract domain from entity_id (e.g. 'light' from 'light.living_room')."""
    return entity_id.split(".")[0]


def get_object_id(entity_id: str) -> str:
    """Extract object_id from entity_id (e.g. 'living_room' from 'light.living_room')."""
    return entity_id.split(".", 1)[1] if "." in entity_id else entity_id


def humanize_object_id(object_id: str) -> str:
    """Convert snake_case object_id to a readable name."""
    return object_id.replace("_", " ").strip()


def infer_location(friendly_name: str, object_id: str) -> str:
    """
    Attempt to infer a room/location from the entity name.
    Returns a string like 'Living Room' or 'Unknown' if not determinable.
    """
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
    """
    Build a rich natural-language document string for a single HA entity.
    This is what gets embedded and stored in ChromaDB.
    """
    entity_id: str = entity.get("entity_id", "")
    state: str = str(entity.get("state", "unknown"))
    attributes: dict = entity.get("attributes", {})

    domain = get_domain(entity_id)
    object_id = get_object_id(entity_id)
    friendly_name: str = attributes.get("friendly_name") or humanize_object_id(object_id)
    domain_desc = DOMAIN_DESCRIPTIONS.get(domain, f"{domain} entity")
    location = infer_location(friendly_name, object_id)

    # Build attribute details
    detail_parts: list[str] = []

    # Device class (motion sensor, door sensor, temperature, etc.)
    device_class = attributes.get("device_class")
    if device_class:
        detail_parts.append(f"device class: {device_class}")

    # Unit of measurement for sensors
    unit = attributes.get("unit_of_measurement")
    if unit:
        detail_parts.append(f"unit: {unit}")

    # Supported features (lights: brightness, color; covers: tilt, etc.)
    supported_color_modes = attributes.get("supported_color_modes", [])
    if supported_color_modes:
        detail_parts.append(f"color modes: {', '.join(supported_color_modes)}")

    # Media player source
    media_content_type = attributes.get("media_content_type")
    if media_content_type:
        detail_parts.append(f"media type: {media_content_type}")

    # Climate modes
    hvac_modes = attributes.get("hvac_modes")
    if hvac_modes:
        detail_parts.append(f"HVAC modes: {', '.join(hvac_modes)}")

    # Source list for media players / selects
    source_list = attributes.get("source_list")
    if source_list and isinstance(source_list, list):
        detail_parts.append(f"sources: {', '.join(str(s) for s in source_list[:5])}")

    details_str = ("; " + "; ".join(detail_parts)) if detail_parts else ""

    doc = (
        f"Entity: {entity_id}\n"
        f"Friendly Name: {friendly_name}\n"
        f"Type: {domain_desc}\n"
        f"Location: {location}\n"
        f"Current State: {state}{details_str}\n"
        f"Domain: {domain}\n"
        f"Object ID: {object_id}"
    )
    return doc


def stable_id(entity_id: str) -> str:
    """Generate a stable ChromaDB document ID from the entity_id."""
    return hashlib.md5(entity_id.encode()).hexdigest()


def fetch_entities(ha_url: str, token: str) -> list[dict]:
    """Fetch all entity states from the HA REST API."""
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
    """Remove noisy/internal entities that aren't useful for Freya."""
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


def import_to_chromadb(
    entities: list[dict],
    chroma_host: str,
    chroma_port: int,
    collection_name: str,
    batch_size: int,
) -> None:
    """Upsert all entities into ChromaDB home_entities collection."""
    try:
        import chromadb
    except ImportError:
        log.error("chromadb package not found. Run: pip install chromadb")
        sys.exit(1)

    log.info(f"Connecting to ChromaDB at {chroma_host}:{chroma_port} ...")
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    # Verify connection
    try:
        client.heartbeat()
        log.info("ChromaDB connection successful.")
    except Exception as e:
        log.error(f"Cannot connect to ChromaDB: {e}")
        sys.exit(1)

    # Get or create the collection (no custom embedding fn — uses ChromaDB default)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Home Assistant entity knowledge base for Freya"},
    )

    existing_count = collection.count()
    log.info(
        f"Collection '{collection_name}' has {existing_count} existing documents. "
        "Upserting all entities (existing entries will be updated)..."
    )

    # Build batches
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

    # Upsert in batches
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
        time.sleep(0.1)  # small pause to avoid overwhelming the server

    final_count = collection.count()
    log.info(
        f"\n✅ Import complete!\n"
        f"   Collection : {collection_name}\n"
        f"   Documents  : {final_count}\n"
        f"   Timestamp  : {now_iso}"
    )


def main() -> None:
    log.info("=" * 60)
    log.info("  Home Assistant → ChromaDB Entity Importer")
    log.info("=" * 60)

    # 1. Fetch entities from HA
    entities = fetch_entities(CONFIG["ha_url"], CONFIG["ha_token"])

    # 2. Filter out noisy domains
    entities = filter_entities(entities, CONFIG["exclude_domains"])

    if not entities:
        log.warning("No entities to import after filtering. Exiting.")
        sys.exit(0)

    # 3. Import into ChromaDB
    import_to_chromadb(
        entities=entities,
        chroma_host=CONFIG["chroma_host"],
        chroma_port=CONFIG["chroma_port"],
        collection_name=CONFIG["collection_name"],
        batch_size=CONFIG["batch_size"],
    )


if __name__ == "__main__":
    main()
