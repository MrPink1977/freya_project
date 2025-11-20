"""Ultra simple test with print statements."""

print("=" * 60)
print("STARTING TEST")
print("=" * 60)

try:
    print("\n1. Importing sounddevice...")
    import sounddevice as sd
    print("   ✓ sounddevice imported")
    
    print("\n2. Checking default device...")
    default_out = sd.default.device[1]
    print(f"   Default output: {default_out}")
    
    print("\n3. Importing config...")
    from pathlib import Path
    from freya.config import load_settings
    print("   ✓ Config module imported")
    
    print("\n4. Loading config file...")
    config = load_settings(Path("config/default.yaml"))
    print(f"   ✓ Config loaded")
    print(f"   TTS Engine: {config.tts.engine}")
    
    print("\n5. Importing TTS...")
    from freya.tts import TextToSpeech
    print("   ✓ TTS imported")
    
    print("\n6. Creating TTS instance...")
    tts = TextToSpeech(config.tts)
    print("   ✓ TTS created")
    
    print("\n7. SPEAKING NOW...")
    tts.speak("Hello! Can you hear me?")
    print("   ✓ Speech complete")
    
    tts.close()
    print("\n8. ✓ ALL TESTS PASSED!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
