#!/usr/bin/env python3
"""Quick test of the performance monitoring tool."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from freya.tools import ToolManager

print("=" * 80)
print("PERFORMANCE MONITORING TOOL TEST")
print("=" * 80)

manager = ToolManager()

# Test 1: Get all performance metrics
print("\nTest 1: All Performance Metrics")
print("-" * 80)
result = manager.execute_tool("performance_monitor", metric="all")
if result.success:
    print("✓ SUCCESS")
    print(result.output)
else:
    print(f"✗ FAILED: {result.error}")

# Test 2: CPU only
print("\n\nTest 2: CPU Usage Only")
print("-" * 80)
result = manager.execute_tool("performance_monitor", metric="cpu")
if result.success:
    print("✓ SUCCESS")
    print(result.output)
else:
    print(f"✗ FAILED: {result.error}")

# Test 3: Memory only
print("\n\nTest 3: Memory Usage Only")
print("-" * 80)
result = manager.execute_tool("performance_monitor", metric="memory")
if result.success:
    print("✓ SUCCESS")
    print(result.output)
else:
    print(f"✗ FAILED: {result.error}")

print("\n" + "=" * 80)
print("Performance monitoring tool test complete!")
print("=" * 80)
