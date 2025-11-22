"""Entry point for Freya TUI."""

from pathlib import Path

from freya.config import load_settings
from freya.ui.app import FreyaApp


def main() -> None:
    """Run Freya TUI."""
    # Load configuration
    config_path = Path("config/default.yaml")

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        print("Please run from the project root directory.")
        return

    try:
        config = load_settings(config_path)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return

    # Create and run TUI app
    app = FreyaApp(config)
    app.run()


if __name__ == "__main__":
    main()
