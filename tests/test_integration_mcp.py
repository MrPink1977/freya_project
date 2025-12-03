"""
Minimal Integration Test Script for Freya MCP v3
Runs 5 automated checks:
1. System server is reachable
2. Directory listing tool works
3. Application open tool works (opens Notepad)
4. Audio STT tool works (transcribes a test WAV)
5. TTS tool works (sends text to ElevenLabs)

Run:
    python -m freya.tests.test_integration_mcp
"""

import os
import time
from freya_mcp.client import FreyaMCPClient
from freya.core.ollama_client import OllamaClient
from freya.coordination.orchestrator_mcp import FreyaMCPOrchestrator

TEST_WAV = "test_audio.wav"  # must exist for STT test
TEST_TEXT = "This is a test of Freya's ElevenLabs voice."


def test_01_system_server(client):
    print("[1] Testing system server tool discovery...")
    tools = client.get_all_tools()
    assert any("freya.system.list_directory" in t for t in tools), \
        "System tools not detected."
    print("    ✓ System server OK")


def test_02_list_directory(client):
    print("[2] Testing list_directory...")
    resp = client.call_tool("freya.system.list_directory", {"path": "."})
    assert resp.get("success"), f"Directory listing failed: {resp}"
    print("    ✓ Directory list returned:", len(resp["items"]), "files")


def test_03_open_application(client):
    print("[3] Testing system.open_application (Notepad)...")
    resp = client.call_tool("freya.system.open_application",
                            {"path": "notepad.exe"})
    assert resp.get("success"), f"Open app failed: {resp}"
    print("    ✓ Notepad launch request sent")
    time.sleep(1)


def test_04_stt(client):
    print("[4] Testing STT via freya.audio.transcribe...")
    assert os.path.exists(TEST_WAV), \
        f"Missing WAV test file: {TEST_WAV}"

    resp = client.call_tool("freya.audio.transcribe",
                            {"file_path": TEST_WAV})
    assert resp.get("success"), f"STT failed: {resp}"
    print("    ✓ Transcription output:", resp["text"][:40], "...")


def test_05_tts(client):
    print("[5] Testing TTS via freya.audio.speak_el...")
    resp = client.call_tool("freya.audio.speak_el",
                            {"text": TEST_TEXT})
    assert resp.get("success"), f"TTS failed: {resp}"
    print("    ✓ ElevenLabs TTS command successful")


def main():
    # 1. Load the MCP client
    config = {
        "system": {"cmd": ["python", "-m", "freya_mcp.servers.freya_system_server.server"]},
        "audio": {"cmd": ["python", "-m", "freya_mcp.servers.freya_audio_server.server"]},
    }

    print("Starting MCP client...")
    client = FreyaMCPClient(config)
    client.start_servers()

    # Execution order:
    test_01_system_server(client)
    test_02_list_directory(client)
    test_03_open_application(client)
    test_04_stt(client)
    test_05_tts(client)

    print("\nALL MCP TESTS PASSED.\n")


if __name__ == "__main__":
    main()
