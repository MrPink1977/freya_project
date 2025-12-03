#!/usr/bin/env python3
"""Simple test for ElevenLabs MCP server communication (no audio playback)."""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path

# Add freya to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_mcp_server():
    """Test MCP server communication."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "AXdMgz6evoL7OPd7eU12")
    
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set in .env file")
        return False
    
    print("🎤 Testing ElevenLabs MCP Server Communication")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"Voice ID: {voice_id}")
    print("=" * 60)
    
    # Find MCP server
    try:
        import elevenlabs_mcp
        server_path = Path(elevenlabs_mcp.__file__).parent / "server.py"
        print(f"\n✅ Found MCP server: {server_path}")
    except ImportError:
        print("\n❌ elevenlabs-mcp not installed")
        return False
    
    # Test 1: List available tools
    print("\n1️⃣  Testing MCP server initialization...")
    env = os.environ.copy()
    env["ELEVENLABS_API_KEY"] = api_key
    env["ELEVENLABS_MCP_OUTPUT_MODE"] = "resources"
    
    # Create a simple MCP request to list tools
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        # Note: MCP servers use stdio, so we need to communicate via stdin/stdout
        print("   Starting MCP server process...")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(server_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        
        # Send request
        print(f"   Sending request: {request['method']}")
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=json.dumps(request).encode()),
            timeout=10.0
        )
        
        if stderr:
            stderr_text = stderr.decode()
            if stderr_text.strip():
                print(f"   Server stderr: {stderr_text[:200]}")
        
        # Parse response
        try:
            response = json.loads(stdout.decode())
            print(f"✅ MCP server responded successfully")
            
            if "result" in response:
                tools = response["result"].get("tools", [])
                print(f"   Found {len(tools)} tools:")
                for tool in tools[:5]:  # Show first 5 tools
                    print(f"     - {tool.get('name', 'unknown')}")
                if len(tools) > 5:
                    print(f"     ... and {len(tools) - 5} more")
                return True
            elif "error" in response:
                print(f"❌ MCP error: {response['error']}")
                return False
            else:
                print(f"⚠️  Unexpected response format: {response}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse MCP response: {e}")
            print(f"   Raw stdout: {stdout.decode()[:500]}")
            return False
            
    except asyncio.TimeoutError:
        print("❌ MCP server timeout")
        return False
    except Exception as exc:
        print(f"❌ MCP server error: {exc}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run tests."""
    try:
        result = asyncio.run(test_mcp_server())
        
        if result:
            print("\n" + "=" * 60)
            print("🎉 MCP server communication test PASSED!")
            print("=" * 60)
            print("\n📝 Next steps:")
            print("   1. MCP server is working correctly")
            print("   2. Ready to integrate with Freya's SpeechAgent")
            print("   3. Audio playback will work on systems with audio devices")
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ MCP server communication test FAILED")
            print("=" * 60)
            return 1
            
    except Exception as exc:
        print(f"\n❌ Test failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
