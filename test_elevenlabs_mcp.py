#!/usr/bin/env python3
"""Test script for ElevenLabs MCP TTS integration."""

import os
import sys
from pathlib import Path

# Add freya to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from freya.voice.tts_elevenlabs_mcp import ElevenLabsMCPTTS

# Load environment variables
load_dotenv()

def main():
    """Test ElevenLabs MCP TTS."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "AXdMgz6evoL7OPd7eU12")
    
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set in .env file")
        return 1
    
    print("🎤 Testing ElevenLabs MCP TTS Integration")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"Voice ID: {voice_id}")
    print("=" * 60)
    
    try:
        print("\n1️⃣  Initializing ElevenLabs MCP TTS...")
        tts = ElevenLabsMCPTTS(
            api_key=api_key,
            voice_id=voice_id,
            model_id="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        )
        print("✅ ElevenLabs MCP TTS initialized successfully")
        
        print("\n2️⃣  Testing text-to-speech...")
        test_text = "Hello! This is a test of the ElevenLabs MCP integration with Freya. If you can hear this, the integration is working perfectly!"
        print(f"Text: {test_text}")
        
        print("\n🔊 Speaking...")
        tts.speak(test_text)
        print("✅ Speech completed successfully")
        
        print("\n3️⃣  Testing short phrase...")
        tts.speak("Integration test successful!")
        print("✅ Short phrase completed")
        
        print("\n" + "=" * 60)
        print("🎉 All tests passed! ElevenLabs MCP TTS is working!")
        print("=" * 60)
        
        return 0
        
    except Exception as exc:
        print(f"\n❌ Test failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
