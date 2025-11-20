"""Test ElevenLabs TTS."""

print("=" * 60)
print("TESTING ELEVENLABS TTS")
print("=" * 60)

try:
    print("\n1. Importing config...")
    from pathlib import Path
    from freya.config import load_settings

    print("\n2. Loading config...")
    config = load_settings(Path("config/default.yaml"))
    print(f"   TTS Engine in config: {config.tts.engine}")
    print(f"   ElevenLabs API Key: {config.tts.elevenlabs.api_key[:20]}...")
    print(f"   ElevenLabs Voice ID: {config.tts.elevenlabs.voice_id}")

    print("\n3. Importing ElevenLabs TTS...")
    from freya.tts_elevenlabs import ElevenLabsTTS

    print("\n4. Creating ElevenLabs TTS instance...")
    tts = ElevenLabsTTS(
        api_key=config.tts.elevenlabs.api_key,
        voice_id=config.tts.elevenlabs.voice_id,
        model_id=config.tts.elevenlabs.model,
    )
    print("   ✓ ElevenLabs TTS created")

    print("\n5. SPEAKING WITH ELEVENLABS NOW...")
    print("   (This might take a moment - cloud API)")
    tts.speak("Hello! I am Freya with ElevenLabs voice. How do I sound?")
    print("   ✓ Speech complete")

    if hasattr(tts, "close"):
        tts.close()

    print("\n6. ✓ ELEVENLABS TEST PASSED!")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Which sounds better - Piper or ElevenLabs?")
print("=" * 60)
