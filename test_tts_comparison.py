"""
Quick test to compare Piper vs ElevenLabs TTS quality.

Usage:
    python test_tts_comparison.py

This will speak the same phrase with both engines so you can compare quality.
"""

import asyncio
import sys
from pathlib import Path

from freya.config import load_settings
from freya.logger import get_logger
from freya.tts import TextToSpeech
from freya.tts_elevenlabs import ElevenLabsTTS

logger = get_logger("tts_test")

TEST_PHRASE = "Hello! I am Freya, your AI assistant. How do I sound?"


async def test_piper(config):
    """Test Piper TTS."""
    print("\n" + "=" * 60)
    print("Testing PIPER (Local TTS)")
    print("=" * 60)
    
    try:
        tts = TextToSpeech(config.tts)
        print(f"Voice: {config.tts.voice_path}")
        print(f"Saying: '{TEST_PHRASE}'")
        print("Speaking...")
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, tts.speak, TEST_PHRASE)
        
        tts.close()
        print("✅ Piper test complete")
        
    except Exception as e:
        print(f"❌ Piper test failed: {e}")
        logger.exception(e)


async def test_elevenlabs(config):
    """Test ElevenLabs TTS."""
    print("\n" + "=" * 60)
    print("Testing ELEVENLABS (Cloud TTS)")
    print("=" * 60)
    
    if not config.tts.elevenlabs.api_key:
        print("❌ ElevenLabs API key not configured")
        print("   Add your API key to config/default.yaml")
        return
    
    try:
        tts = ElevenLabsTTS(
            api_key=config.tts.elevenlabs.api_key,
            voice_id=config.tts.elevenlabs.voice_id,
            model=config.tts.elevenlabs.model,
        )
        
        print(f"Voice ID: {config.tts.elevenlabs.voice_id}")
        print(f"Model: {config.tts.elevenlabs.model}")
        print(f"Saying: '{TEST_PHRASE}'")
        print("Speaking...")
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, tts.speak, TEST_PHRASE)
        
        tts.close()
        print("✅ ElevenLabs test complete")
        
    except Exception as e:
        print(f"❌ ElevenLabs test failed: {e}")
        logger.exception(e)


async def main():
    """Main test function."""
    # Load config
    config_path = Path("config/default.yaml")
    if not config_path.exists():
        print("❌ Config file not found: config/default.yaml")
        sys.exit(1)
    
    try:
        config = load_settings(config_path)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("  FREYA TTS COMPARISON TEST")
    print("=" * 60)
    print("\nYou will hear the same phrase spoken by:")
    print("  1. Piper (local, fast, free)")
    print("  2. ElevenLabs (cloud, premium, requires API key)")
    print("\nListen carefully and decide which sounds better!")
    print("=" * 60)
    
    input("\nPress Enter to start test...")
    
    # Test Piper
    await test_piper(config)
    
    await asyncio.sleep(1)  # Brief pause between tests
    
    # Test ElevenLabs
    await test_elevenlabs(config)
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)
    print("\nWhich sounded better?")
    print("  - Piper: Fast, works offline, completely free")
    print("  - ElevenLabs: Premium quality, requires internet + API key")
    print("\nTo change TTS engine:")
    print("  1. Edit config/default.yaml")
    print("  2. Change 'tts.engine' to 'piper' or 'elevenlabs'")
    print("  3. Or use: python main.py --engine elevenlabs")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Interrupted] Test cancelled")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
