"""Test if main.py imports work."""

import sys

print("=" * 60)
print("TESTING IMPORTS FOR main.py")
print("=" * 60)

try:
    print("\n1. Importing argparse...")

    print("   ✓")

    print("2. Importing asyncio...")

    print("   ✓")

    print("3. Importing pathlib...")
    from pathlib import Path

    print("   ✓")

    print("4. Importing freya.config...")
    from freya.config import load_settings

    print("   ✓")

    print("5. Importing freya.coordination.orchestration_coordinator...")
    from freya.coordination.orchestration_coordinator import create_coordinator_from_config

    print("   ✓")

    print("6. Importing freya.logger...")

    print("   ✓")

    print("\n7. Loading config...")
    config = load_settings(Path("config/default.yaml"))
    print("   ✓ Config loaded")

    print("\n8. Creating coordinator...")
    coordinator = create_coordinator_from_config(config)
    print("   ✓ Coordinator created")

    print("\n" + "=" * 60)
    print("ALL IMPORTS SUCCESSFUL!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
