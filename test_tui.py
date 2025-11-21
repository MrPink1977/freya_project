"""Test script to check if TUI can launch."""

import sys
print("Python executable:", sys.executable)
print("Python version:", sys.version)

try:
    print("\n1. Importing freya.config...")
    from freya.config import load_settings
    print("   ✓ freya.config imported")
    
    print("\n2. Loading config from config/default.yaml...")
    from pathlib import Path
    config_path = Path("config/default.yaml")
    if config_path.exists():
        print(f"   ✓ Config file exists: {config_path}")
        config = load_settings(config_path)
        print(f"   ✓ Config loaded successfully")
        print(f"   - Interaction mode: {config.app.interaction_mode}")
        print(f"   - Dialog model: {config.dialog.model}")
    else:
        print(f"   ✗ Config file NOT found: {config_path}")
        sys.exit(1)
    
    print("\n3. Importing textual...")
    import textual
    print(f"   ✓ Textual version: {textual.__version__}")
    
    print("\n4. Importing FreyaApp...")
    from freya.ui.app import FreyaApp
    print("   ✓ FreyaApp imported")
    
    print("\n5. Creating FreyaApp instance...")
    app = FreyaApp(config)
    print("   ✓ FreyaApp created")
    
    print("\n6. Running app...")
    print("   (This will take over your terminal - press F10 or Ctrl+C to exit)")
    app.run()
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
