"""
build_home_entities.py  —  Freya Home Entities Ingestion (Verified)
====================================================================
Loads a hand-verified, user-confirmed set of Home Assistant entities
into ChromaDB collection 'home_entities' using nomic-embed-text via Ollama.

This script uses a HARDCODED verified entity list (not auto-discovery)
so that only real, confirmed devices are indexed — no phantom entries,
no duplicate TV integrations, no internal system entities.

Panel map verified against physical breaker panel on 2026-03-04.

Usage:
    python build_home_entities.py

Requirements:
    pip install requests chromadb tqdm
"""

import uuid
import requests
from tqdm import tqdm

# --- Settings ---
OLLAMA_HOST     = "http://localhost:11434"
EMBED_MODEL     = "nomic-embed-text:latest"
CHROMA_HOST     = "localhost"
CHROMA_PORT     = 8000
COLLECTION_NAME = "home_entities"

# =============================================================================
# VERIFIED ENTITY LIST  (user-confirmed 2026-03-04)
# Format: (entity_id, friendly_name, room, device_type, description, aliases)
# =============================================================================
VERIFIED_ENTITIES = [

    # -------------------------------------------------------------------------
    # BEDROOM (War Room)
    # -------------------------------------------------------------------------
    (
        "light.counterlamp1",
        "Left Lamp",
        "bedroom",
        "light",
        "Smart color bulb on the left side of the bedroom. Can be turned on/off, dimmed, or color-changed.",
        ["left lamp", "left light", "bedroom left lamp"]
    ),
    (
        "light.counterlamp2",
        "Right Lamp",
        "bedroom",
        "light",
        "Smart color bulb on the right side of the bedroom. Can be turned on/off, dimmed, or color-changed.",
        ["right lamp", "right light", "bedroom right lamp"]
    ),
    (
        "light.biglamp1",
        "Big Lamp One",
        "bedroom",
        "light",
        "Smart color floor/table lamp in the bedroom. Can be turned on/off, dimmed, or color-changed.",
        ["big lamp one", "big lamp 1", "lamp one", "first big lamp"]
    ),
    (
        "light.biglamp2",
        "Big Lamp Two",
        "bedroom",
        "light",
        "Smart color floor/table lamp in the bedroom. Can be turned on/off, dimmed, or color-changed.",
        ["big lamp two", "big lamp 2", "lamp two", "second big lamp"]
    ),
    (
        "light.ceilingfanlight",
        "Ceiling Fan Light",
        "bedroom",
        "light",
        "Smart color bulb in the bedroom ceiling fan. Can be turned on/off, dimmed, or color-changed.",
        ["ceiling fan light", "ceiling light", "fan light", "bedroom ceiling"]
    ),
    (
        "light.home_assistant_voice_0a52fa_led_ring",
        "VoicePE LED Ring",
        "bedroom",
        "light",
        "LED ring light on the Home Assistant Voice PE device in the bedroom. Indicates assistant status.",
        ["voice pe light", "voice assistant light", "led ring", "voicebox light"]
    ),
    (
        "assist_satellite.home_assistant_voice_0a52fa_assist_satellite",
        "VoicePE Assist Satellite",
        "bedroom",
        "voice_assistant",
        "Home Assistant Voice PE device in the bedroom. The primary voice assistant satellite for the home.",
        ["voice pe", "voice assistant", "voicebox", "hey freya device", "the assistant"]
    ),
    (
        "media_player.android_tv_192_168_68_60",
        "Bedroom TV",
        "bedroom",
        "media_player",
        "Android TV in the bedroom (also called the War Room TV). Can play, pause, stop, change volume, change source, or launch apps.",
        ["tv", "bedroom tv", "war room tv", "the tv", "android tv", "television"]
    ),

    # -------------------------------------------------------------------------
    # FRONT DOOR / OUTSIDE
    # -------------------------------------------------------------------------
    (
        "light.porchlight",
        "Porch Light",
        "front door",
        "light",
        "Smart porch light at the front door. Can be turned on or off.",
        ["porch light", "front door light", "front light", "porch lamp"]
    ),
    (
        "light.motion_light_floodlight",
        "Front Door Floodlight",
        "front door",
        "light",
        "Reolink camera floodlight at the front door. Activates on motion or can be manually controlled.",
        ["floodlight", "flood light", "front door floodlight", "reolink light", "driveway light", "motion light"]
    ),
    (
        "camera.motion_light_fluent",
        "Front Door Camera (Live)",
        "front door",
        "camera",
        "Reolink camera live feed at the front door. Shows real-time video of the front door area.",
        ["front door camera", "front camera", "reolink camera", "driveway camera", "motion camera"]
    ),
    (
        "camera.front_door_snapshots_fluent",
        "Front Door Camera (Snapshots)",
        "front door",
        "camera",
        "Reolink camera snapshot feed at the front door. Provides still image snapshots of the front door.",
        ["front door snapshot", "front door photo", "door camera snapshot"]
    ),
    (
        "siren.motion_light_siren",
        "Front Door Siren",
        "front door",
        "siren",
        "Reolink camera siren at the front door. Can be triggered as an alarm or deterrent.",
        ["front door siren", "reolink siren", "door alarm", "front siren"]
    ),
    (
        "switch.motion_light_infrared_lights_in_night_mode",
        "Front Door IR Night Mode",
        "front door",
        "switch",
        "Reolink camera infrared night vision mode switch. Enables/disables IR lights for night recording.",
        ["night mode", "infrared", "ir mode", "night vision"]
    ),
    (
        "switch.motion_light_record",
        "Front Door Recording",
        "front door",
        "switch",
        "Reolink camera recording switch. Enables or disables video recording at the front door.",
        ["front door recording", "camera recording", "reolink record"]
    ),
    (
        "switch.motion_light_record_audio",
        "Front Door Audio Recording",
        "front door",
        "switch",
        "Reolink camera audio recording switch. Enables or disables audio capture with video.",
        ["audio recording", "camera audio", "record audio"]
    ),
    (
        "switch.motion_light_push_notifications",
        "Front Door Push Notifications",
        "front door",
        "switch",
        "Reolink camera push notification switch. Enables or disables mobile alerts on motion detection.",
        ["push notifications", "camera notifications", "door alerts", "motion alerts"]
    ),
    (
        "switch.motion_light_siren_on_event",
        "Front Door Siren on Motion",
        "front door",
        "switch",
        "Reolink camera setting: automatically trigger siren when motion is detected.",
        ["siren on motion", "auto siren", "motion siren"]
    ),
    (
        "switch.motion_light_email_on_event",
        "Front Door Email on Motion",
        "front door",
        "switch",
        "Reolink camera setting: send email alert when motion is detected.",
        ["email on motion", "motion email", "camera email alert"]
    ),
    (
        "switch.motion_light_ftp_upload",
        "Front Door FTP Upload",
        "front door",
        "switch",
        "Reolink camera FTP upload switch. Enables or disables uploading recordings to an FTP server.",
        ["ftp upload", "camera ftp", "upload recordings"]
    ),

    # -------------------------------------------------------------------------
    # LIVING ROOM
    # -------------------------------------------------------------------------
    (
        "cover.awesome_table",
        "Awesome Table",
        "living room",
        "cover",
        "Motorized ESP32-controlled table in the living room. Reports open/closed state.",
        ["awesome table", "the table", "motorized table", "living room table", "smart table"]
    ),
    (
        "script.open_table",
        "Open Table",
        "living room",
        "script",
        "Opens (raises) the Awesome Table in the living room. ESP32 controlled via 192.168.68.71.",
        ["open the table", "raise the table", "table up"]
    ),
    (
        "script.close_table",
        "Close Table",
        "living room",
        "script",
        "Closes (lowers) the Awesome Table in the living room. ESP32 controlled via 192.168.68.71.",
        ["close the table", "lower the table", "table down"]
    ),
    (
        "script.stop_table",
        "Stop Table",
        "living room",
        "script",
        "Stops the Awesome Table mid-movement. ESP32 controlled via 192.168.68.71.",
        ["stop the table", "table stop", "halt table"]
    ),

    # -------------------------------------------------------------------------
    # SHOPPING LIST & CALENDAR
    # -------------------------------------------------------------------------
    (
        "todo.shopping_list",
        "Shopping List",
        "home",
        "todo",
        "Home Assistant shopping list. Items can be added, removed, or read back by voice.",
        ["shopping list", "grocery list", "shopping", "groceries", "buy list"]
    ),
    (
        "calendar.local_calendar",
        "Local Calendar",
        "home",
        "calendar",
        "Home Assistant local calendar. Events can be added, removed, or queried by voice.",
        ["calendar", "my calendar", "schedule", "appointments", "events"]
    ),

    # -------------------------------------------------------------------------
    # AUTOMATIONS
    # -------------------------------------------------------------------------
    (
        "automation.driveway_alarm2",
        "Driveway Alarm",
        "front door",
        "automation",
        "Automation that triggers an alert when motion is detected in the driveway.",
        ["driveway alarm", "driveway alert", "driveway motion"]
    ),
    (
        "automation.fllod_light_announcment",
        "Front Door Motion Announcement",
        "front door",
        "automation",
        "Automation that makes an announcement when motion is detected at the front door.",
        ["front door announcement", "door motion announcement", "flood light announcement"]
    ),
    (
        "automation.front_door_night_light",
        "Front Door Night Light",
        "front door",
        "automation",
        "Automation that turns on the porch light at night automatically.",
        ["front door night light", "porch light automation", "night light automation"]
    ),
    (
        "automation.new_automation",
        "Random Kanye Quote",
        "home",
        "automation",
        "Automation that plays a random clean Kanye West quote.",
        ["kanye quote", "random quote", "kanye automation"]
    ),
    (
        "automation.porchlight",
        "Porch Light Automation",
        "front door",
        "automation",
        "Automation controlling the porch light behavior.",
        ["porch light automation", "porch automation"]
    ),
    (
        "automation.conversation_listening",
        "Conversation Listening",
        "bedroom",
        "automation",
        "Automation that manages the voice assistant conversation listening state.",
        ["conversation listening", "listening automation"]
    ),
    (
        "automation.voice_pe_stop_on_thank_you",
        "Voice PE Stop on Thank You",
        "bedroom",
        "automation",
        "Automation that stops the Voice PE listening session when the user says thank you.",
        ["stop on thank you", "thank you automation"]
    ),
    (
        "automation.voice_pe_follow_up_listening_window",
        "Voice PE Follow-up Listening",
        "bedroom",
        "automation",
        "Automation that keeps the Voice PE in listening mode for follow-up commands after a response.",
        ["follow up listening", "listening window"]
    ),
    (
        "automation.voice_pe_stop_on_closing_phrase",
        "Voice PE Stop on Closing Phrase",
        "bedroom",
        "automation",
        "Automation that stops the Voice PE listening session when a closing phrase is detected.",
        ["stop on closing phrase", "closing phrase automation"]
    ),

    # -------------------------------------------------------------------------
    # POWER CENTER — SEM B (Leg 2 / B side of panel)
    # Each CT channel has 3 sensors: current (A), active power (W), voltage (V)
    # -------------------------------------------------------------------------
    (
        "sensor.sem_b_ch01_current",
        "Bedroom Mini Split — Current",
        "power center",
        "sensor",
        "SEM B Channel 1 — Breaker 2. Current draw (Amps) of the bedroom mini split air conditioner.",
        ["bedroom mini split current", "mini split amps", "bedroom ac current"]
    ),
    (
        "sensor.sem_b_ch01_active_power",
        "Bedroom Mini Split — Power",
        "power center",
        "sensor",
        "SEM B Channel 1 — Breaker 2. Active power (Watts) used by the bedroom mini split air conditioner.",
        ["bedroom mini split power", "mini split watts", "bedroom ac power", "bedroom ac usage"]
    ),
    (
        "sensor.sem_b_ch01_voltage",
        "Bedroom Mini Split — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 1 — Breaker 2. Voltage (Volts) at the bedroom mini split circuit.",
        ["bedroom mini split voltage"]
    ),
    (
        "sensor.sem_b_ch02_current",
        "Tool Room Lights & Garage Door — Current",
        "power center",
        "sensor",
        "SEM B Channel 2 — Breaker 6. Current draw (Amps) for tool room lights and garage door.",
        ["tool room lights current", "garage door current"]
    ),
    (
        "sensor.sem_b_ch02_active_power",
        "Tool Room Lights & Garage Door — Power",
        "power center",
        "sensor",
        "SEM B Channel 2 — Breaker 6. Active power (Watts) for tool room lights and garage door.",
        ["tool room lights power", "garage door power"]
    ),
    (
        "sensor.sem_b_ch02_voltage",
        "Tool Room Lights & Garage Door — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 2 — Breaker 6. Voltage at tool room lights and garage door circuit.",
        ["tool room voltage"]
    ),
    (
        "sensor.sem_b_ch03_current",
        "Dryer & Oven — Current",
        "power center",
        "sensor",
        "SEM B Channel 3 — Breakers 8+10 (double-pole). Current draw (Amps) for the dryer and oven.",
        ["dryer current", "oven current", "dryer oven current"]
    ),
    (
        "sensor.sem_b_ch03_active_power",
        "Dryer & Oven — Power",
        "power center",
        "sensor",
        "SEM B Channel 3 — Breakers 8+10 (double-pole). Active power (Watts) for the dryer and oven.",
        ["dryer power", "oven power", "dryer watts", "oven watts"]
    ),
    (
        "sensor.sem_b_ch03_voltage",
        "Dryer & Oven — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 3 — Breakers 8+10 (double-pole). Voltage at dryer and oven circuit.",
        ["dryer voltage", "oven voltage"]
    ),
    (
        "sensor.sem_b_ch04_current",
        "Water Heater — Current",
        "power center",
        "sensor",
        "SEM B Channel 4 — Breaker 12. Current draw (Amps) of the water heater.",
        ["water heater current", "hot water current"]
    ),
    (
        "sensor.sem_b_ch04_active_power",
        "Water Heater — Power",
        "power center",
        "sensor",
        "SEM B Channel 4 — Breaker 12. Active power (Watts) used by the water heater.",
        ["water heater power", "water heater watts", "hot water power"]
    ),
    (
        "sensor.sem_b_ch04_voltage",
        "Water Heater — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 4 — Breaker 12. Voltage at the water heater circuit.",
        ["water heater voltage"]
    ),
    (
        "sensor.sem_b_ch05_current",
        "Bedroom Outlets East — Current",
        "power center",
        "sensor",
        "SEM B Channel 5 — Breaker 14. Current draw (Amps) for bedroom outlets on the east side.",
        ["bedroom outlets east current", "bedroom east current"]
    ),
    (
        "sensor.sem_b_ch05_active_power",
        "Bedroom Outlets East — Power",
        "power center",
        "sensor",
        "SEM B Channel 5 — Breaker 14. Active power (Watts) for bedroom outlets on the east side.",
        ["bedroom outlets east power", "bedroom east power"]
    ),
    (
        "sensor.sem_b_ch05_voltage",
        "Bedroom Outlets East — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 5 — Breaker 14. Voltage at bedroom east outlets circuit.",
        ["bedroom east voltage"]
    ),
    (
        "sensor.sem_b_ch06_current",
        "Tool Room Outlets — Current",
        "power center",
        "sensor",
        "SEM B Channel 6 — Breaker 16. Current draw (Amps) for tool room outlets.",
        ["tool room outlets current", "tool room current"]
    ),
    (
        "sensor.sem_b_ch06_active_power",
        "Tool Room Outlets — Power",
        "power center",
        "sensor",
        "SEM B Channel 6 — Breaker 16. Active power (Watts) for tool room outlets.",
        ["tool room outlets power", "tool room power"]
    ),
    (
        "sensor.sem_b_ch06_voltage",
        "Tool Room Outlets — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 6 — Breaker 16. Voltage at tool room outlets circuit.",
        ["tool room outlets voltage"]
    ),
    (
        "sensor.sem_b_ch07_current",
        "Greenhouse Outlets (Main) — Current",
        "power center",
        "sensor",
        "SEM B Channel 7 — Breakers 18+20 (double-pole). Current draw (Amps) for greenhouse main outlets.",
        ["greenhouse outlets current", "greenhouse current", "gh outlets current"]
    ),
    (
        "sensor.sem_b_ch07_active_power",
        "Greenhouse Outlets (Main) — Power",
        "power center",
        "sensor",
        "SEM B Channel 7 — Breakers 18+20 (double-pole). Active power (Watts) for greenhouse main outlets.",
        ["greenhouse outlets power", "greenhouse power", "gh power"]
    ),
    (
        "sensor.sem_b_ch07_voltage",
        "Greenhouse Outlets (Main) — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 7 — Breakers 18+20 (double-pole). Voltage at greenhouse main outlets circuit.",
        ["greenhouse voltage"]
    ),
    (
        "sensor.sem_ch08_porchlight_22_current",
        "Porch Light Circuit — Current",
        "power center",
        "sensor",
        "SEM B Channel 8 — Breaker 22. Current draw (Amps) on the porch light circuit.",
        ["porch light current", "porch circuit current"]
    ),
    (
        "sensor.sem_ch08_porchlight_22_active_power",
        "Porch Light Circuit — Power",
        "power center",
        "sensor",
        "SEM B Channel 8 — Breaker 22. Active power (Watts) on the porch light circuit.",
        ["porch light power", "porch circuit power"]
    ),
    (
        "sensor.sem_ch08_porchlight_22_voltage",
        "Porch Light Circuit — Voltage",
        "power center",
        "sensor",
        "SEM B Channel 8 — Breaker 22. Voltage on the porch light circuit.",
        ["porch light voltage"]
    ),

    # -------------------------------------------------------------------------
    # POWER CENTER — SEM C (Leg 1 / A side of panel)
    # -------------------------------------------------------------------------
    (
        "sensor.sem_ch09_outlets_grhouse_19_current",
        "Greenhouse Outlets (Secondary) — Current",
        "power center",
        "sensor",
        "SEM C Channel 9 — Breaker 19. Current draw (Amps) for secondary greenhouse outlets.",
        ["greenhouse secondary current", "greenhouse outlets 2 current"]
    ),
    (
        "sensor.sem_ch09_outlets_grhouse_19_active_power",
        "Greenhouse Outlets (Secondary) — Power",
        "power center",
        "sensor",
        "SEM C Channel 9 — Breaker 19. Active power (Watts) for secondary greenhouse outlets.",
        ["greenhouse secondary power", "greenhouse outlets 2 power"]
    ),
    (
        "sensor.sem_ch09_outlets_grhouse_19_voltage",
        "Greenhouse Outlets (Secondary) — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 9 — Breaker 19. Voltage at secondary greenhouse outlets circuit.",
        ["greenhouse secondary voltage"]
    ),
    (
        "sensor.sem_ch10_minisplit_grhouse_15_current",
        "Greenhouse Mini Split — Current",
        "power center",
        "sensor",
        "SEM C Channel 10 — Breaker 15. Current draw (Amps) of the greenhouse mini split.",
        ["greenhouse mini split current", "gh mini split current", "greenhouse ac current"]
    ),
    (
        "sensor.sem_ch10_minisplit_grhouse_15_active_power",
        "Greenhouse Mini Split — Power",
        "power center",
        "sensor",
        "SEM C Channel 10 — Breaker 15. Active power (Watts) used by the greenhouse mini split.",
        ["greenhouse mini split power", "gh mini split power", "greenhouse ac power"]
    ),
    (
        "sensor.sem_ch10_minisplit_grhouse_15_voltage",
        "Greenhouse Mini Split — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 10 — Breaker 15. Voltage at the greenhouse mini split circuit.",
        ["greenhouse mini split voltage"]
    ),
    (
        "sensor.sem_ch11_outlets_outside_west_13_current",
        "Outside Outlets West — Current",
        "power center",
        "sensor",
        "SEM C Channel 11 — Breaker 13. Current draw (Amps) for outside outlets on the west side.",
        ["outside outlets west current", "west outlets current", "outside west current"]
    ),
    (
        "sensor.sem_ch11_outlets_outside_west_13_active_power",
        "Outside Outlets West — Power",
        "power center",
        "sensor",
        "SEM C Channel 11 — Breaker 13. Active power (Watts) for outside outlets on the west side.",
        ["outside outlets west power", "west outlets power"]
    ),
    (
        "sensor.sem_ch11_outlets_outside_west_13_voltage",
        "Outside Outlets West — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 11 — Breaker 13. Voltage at outside west outlets circuit.",
        ["outside west voltage"]
    ),
    (
        "sensor.sem_ch12_septic_aerator_11_current",
        "Septic Aerator — Current",
        "power center",
        "sensor",
        "SEM C Channel 12 — Breaker 11. Current draw (Amps) of the septic aerator pump.",
        ["septic aerator current", "septic current", "aerator current"]
    ),
    (
        "sensor.sem_ch12_septic_aerator_11_active_power",
        "Septic Aerator — Power",
        "power center",
        "sensor",
        "SEM C Channel 12 — Breaker 11. Active power (Watts) used by the septic aerator pump.",
        ["septic aerator power", "septic power", "aerator power"]
    ),
    (
        "sensor.sem_ch12_septic_aerator_11_voltage",
        "Septic Aerator — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 12 — Breaker 11. Voltage at the septic aerator circuit.",
        ["septic voltage"]
    ),
    (
        "sensor.sem_ch13_mainlights_9_current",
        "Garage & Main Lights — Current",
        "power center",
        "sensor",
        "SEM C Channel 13 — Breaker 9. Current draw (Amps) for garage and main house lights.",
        ["garage lights current", "main lights current"]
    ),
    (
        "sensor.sem_ch13_mainlights_9_active_power",
        "Garage & Main Lights — Power",
        "power center",
        "sensor",
        "SEM C Channel 13 — Breaker 9. Active power (Watts) for garage and main house lights.",
        ["garage lights power", "main lights power"]
    ),
    (
        "sensor.sem_ch13_mainlights_9_voltage",
        "Garage & Main Lights — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 13 — Breaker 9. Voltage at garage and main lights circuit.",
        ["garage lights voltage"]
    ),
    (
        "sensor.sem_ch14_outlets_bedroom_bench_7_current",
        "Kitchen Outlets — Current",
        "power center",
        "sensor",
        "SEM C Channel 14 — Breaker 7. Current draw (Amps) for kitchen outlets.",
        ["kitchen outlets current", "kitchen current"]
    ),
    (
        "sensor.sem_ch14_outlets_bedroom_bench_7_active_power",
        "Kitchen Outlets — Power",
        "power center",
        "sensor",
        "SEM C Channel 14 — Breaker 7. Active power (Watts) for kitchen outlets.",
        ["kitchen outlets power", "kitchen power"]
    ),
    (
        "sensor.sem_ch14_outlets_bedroom_bench_7_voltage",
        "Kitchen Outlets — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 14 — Breaker 7. Voltage at kitchen outlets circuit.",
        ["kitchen voltage"]
    ),
    (
        "sensor.sem_ch15_outlets_bdrm_n_light_bench_5_current",
        "Bedroom Outlets North — Current",
        "power center",
        "sensor",
        "SEM C Channel 15 — Breaker 5. Current draw (Amps) for bedroom outlets on the north side.",
        ["bedroom outlets north current", "bedroom north current"]
    ),
    (
        "sensor.sem_ch15_outlets_bdrm_n_light_bench_5_active_power",
        "Bedroom Outlets North — Power",
        "power center",
        "sensor",
        "SEM C Channel 15 — Breaker 5. Active power (Watts) for bedroom outlets on the north side.",
        ["bedroom outlets north power", "bedroom north power"]
    ),
    (
        "sensor.sem_ch15_outlets_bdrm_n_light_bench_5_voltage",
        "Bedroom Outlets North — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 15 — Breaker 5. Voltage at bedroom north outlets circuit.",
        ["bedroom north voltage"]
    ),
    (
        "sensor.sem_ch16_garage_heater_3_current",
        "Garage Heater — Current",
        "power center",
        "sensor",
        "SEM C Channel 16 — Breaker 1. Current draw (Amps) of the garage heater.",
        ["garage heater current", "garage heater amps"]
    ),
    (
        "sensor.sem_ch16_garage_heater_3_active_power",
        "Garage Heater — Power",
        "power center",
        "sensor",
        "SEM C Channel 16 — Breaker 1. Active power (Watts) used by the garage heater.",
        ["garage heater power", "garage heater watts"]
    ),
    (
        "sensor.sem_ch16_garage_heater_3_voltage",
        "Garage Heater — Voltage",
        "power center",
        "sensor",
        "SEM C Channel 16 — Breaker 1. Voltage at the garage heater circuit.",
        ["garage heater voltage"]
    ),

    # -------------------------------------------------------------------------
    # MOBILE DEVICES (useful for presence/battery queries)
    # -------------------------------------------------------------------------
    (
        "sensor.tomies_iphone_battery_level",
        "Tomie's iPhone Battery Level",
        "mobile",
        "sensor",
        "Battery level percentage of Tomie's iPhone.",
        ["iphone battery", "phone battery", "my phone battery", "tomie iphone battery"]
    ),
    (
        "sensor.tomies_iphone_battery_state",
        "Tomie's iPhone Battery State",
        "mobile",
        "sensor",
        "Battery charging state of Tomie's iPhone (charging, discharging, full).",
        ["iphone charging", "phone charging state", "is my phone charging"]
    ),
    (
        "sensor.tomies_ipad_battery_level",
        "Tomie's iPad Battery Level",
        "mobile",
        "sensor",
        "Battery level percentage of Tomie's iPad.",
        ["ipad battery", "tablet battery", "tomie ipad battery"]
    ),
    (
        "sensor.tomies_ipad_battery_state",
        "Tomie's iPad Battery State",
        "mobile",
        "sensor",
        "Battery charging state of Tomie's iPad (charging, discharging, full).",
        ["ipad charging", "is the ipad charging"]
    ),
]


def build_document(entity_id, friendly_name, room, device_type, description, aliases):
    """Build a rich semantic document for a single entity."""
    doc = f"""Entity: {friendly_name}
Entity ID: {entity_id}
Room / Location: {room}
Device Type: {device_type}
Description: {description}
Also known as: {', '.join(aliases)}
"""
    metadata = {
        "entity_id":     entity_id,
        "friendly_name": friendly_name,
        "room":          room,
        "device_type":   device_type,
    }
    return doc, metadata


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
    print("\n=== Freya Home Entities Ingestion (Verified) ===\n")
    print(f"Total verified entities to ingest: {len(VERIFIED_ENTITIES)}\n")

    # Verify Ollama
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

    # Connect to ChromaDB
    print(f"\nConnecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
    import chromadb
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    # Delete and recreate collection for clean load
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

    # Embed and ingest
    print(f"Embedding and ingesting {len(VERIFIED_ENTITIES)} entities...")
    ids, embeddings, documents, metadatas = [], [], [], []

    for entity in tqdm(VERIFIED_ENTITIES, desc="Embedding"):
        entity_id, friendly_name, room, device_type, description, aliases = entity
        doc_text, metadata = build_document(
            entity_id, friendly_name, room, device_type, description, aliases
        )
        try:
            embedding = get_embedding(doc_text)
        except Exception as ex:
            print(f"\n  SKIP {entity_id}: {ex}")
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
    print(f"  Freya can now resolve all verified home entities.")
    print(f"=================================================\n")

    # Summary by room
    from collections import Counter
    rooms = Counter(e[2] for e in VERIFIED_ENTITIES)
    print("Entities by room:")
    for room, count in sorted(rooms.items()):
        print(f"  {room:<20} {count} entities")
    print()


if __name__ == "__main__":
    main()
