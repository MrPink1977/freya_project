"""Simple test to verify TUI works."""

from pathlib import Path
from freya.config import load_settings
from freya.ui.app import FreyaApp

print("Starting Freya TUI...")
print("Loading config...")

config_path = Path("config/default.yaml")
config = load_settings(config_path)

print(f"Config loaded: {config.app.interaction_mode}")
print("Launching TUI (press F10 or Ctrl+C to exit)...")
print()

app = FreyaApp(config)
app.run()

print("\nTUI exited.")
