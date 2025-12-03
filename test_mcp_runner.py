#!/usr/bin/env python3
"""
Standalone test script for MCP servers that avoids importing the freya package.
"""

import sys
import subprocess

def test_server_list():
    """Test listing available servers."""
    print("=" * 60)
    print("TEST: List Available Servers")
    print("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "-m", "freya.run_mcp_servers", "--list"],
        cwd="/home/ubuntu/freya_project",
        capture_output=True,
        text=True
    )
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"Return code: {result.returncode}")
    print()
    
    return result.returncode == 0

def test_server_import(server_name):
    """Test importing a specific server module."""
    print("=" * 60)
    print(f"TEST: Import {server_name} Server")
    print("=" * 60)
    
    code = f"""
import sys
sys.path.insert(0, '/home/ubuntu/freya_project')

try:
    from freya.mcp_servers.{server_name}_server import server
    print(f"✓ Successfully imported {server_name}_server")
    print(f"  Server name: {{server.name}}")
except Exception as e:
    print(f"✗ Failed to import {server_name}_server: {{e}}")
    sys.exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"Return code: {result.returncode}")
    print()
    
    return result.returncode == 0

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MCP SERVER INTEGRATION TESTS")
    print("=" * 60 + "\n")
    
    results = {}
    
    # Test server imports
    for server in ["system", "file", "web", "audio", "vision"]:
        results[f"import_{server}"] = test_server_import(server)
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print()
    print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print()
    
    sys.exit(0 if all_passed else 1)
