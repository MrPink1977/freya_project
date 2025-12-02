#!/usr/bin/env python3
"""
Phase 2 Testing: System & Performance Tools

Quick test of system_info and performance_monitor tools.
These require no special hardware - they just read system stats.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Direct import to avoid config loading
import importlib.util

def load_module(name, path):
    """Load module without triggering full package imports."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f'freya.tools.{name}'] = module
    return module, spec

# Load base module first
base_module, base_spec = load_module('base', Path(__file__).parent / "freya" / "tools" / "base.py")
base_spec.loader.exec_module(base_module)

# Load system_tools
system_module, system_spec = load_module('system_tools', Path(__file__).parent / "freya" / "tools" / "system_tools.py")
system_spec.loader.exec_module(system_module)

# Load performance_tools
perf_module, perf_spec = load_module('performance_tools', Path(__file__).parent / "freya" / "tools" / "performance_tools.py")
perf_spec.loader.exec_module(perf_module)

SystemInfoTool = system_module.SystemInfoTool
PerformanceMonitorTool = perf_module.PerformanceMonitorTool


def print_test(name: str):
    """Print test header."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)


def print_result(result, expected_success=True):
    """Print tool result."""
    if result.success == expected_success:
        status = "✅ PASS"
    else:
        status = "❌ FAIL"

    print(f"{status}")
    print(f"Success: {result.success}")
    if result.output:
        # Limit output for readability
        output = result.output[:500] + "..." if len(result.output) > 500 else result.output
        print(f"Output:\n{output}")
    if result.error:
        print(f"Error: {result.error}")


def test_system_info():
    """Test SystemInfoTool."""
    tool = SystemInfoTool()

    # Test 1: Get all system info
    print_test("SystemInfoTool - Get all system information")
    result = tool.execute()
    print_result(result, expected_success=True)

    # Test 2: Get OS info only
    print_test("SystemInfoTool - OS information only")
    result = tool.execute(info_type="os")
    print_result(result, expected_success=True)

    # Test 3: Get Python info only
    print_test("SystemInfoTool - Python information only")
    result = tool.execute(info_type="python")
    print_result(result, expected_success=True)

    # Test 4: Get disk info only
    print_test("SystemInfoTool - Disk space information")
    result = tool.execute(info_type="disk")
    print_result(result, expected_success=True)


def test_performance_monitor():
    """Test PerformanceMonitorTool."""
    tool = PerformanceMonitorTool()

    # Check if psutil is available
    try:
        import psutil
        psutil_available = True
    except ImportError:
        psutil_available = False
        print("\n⚠️  psutil not installed - performance tests will show graceful errors")

    # Test 1: Get all performance metrics
    print_test("PerformanceMonitor - All metrics")
    result = tool.execute()
    if psutil_available:
        print_result(result, expected_success=True)
    else:
        print_result(result, expected_success=False)
        print("(Expected failure - psutil not installed)")

    # Test 2: Get CPU only
    print_test("PerformanceMonitor - CPU metrics only")
    result = tool.execute(metric="cpu")
    if psutil_available:
        print_result(result, expected_success=True)
    else:
        print_result(result, expected_success=False)
        print("(Expected failure - psutil not installed)")

    # Test 3: Get memory only
    print_test("PerformanceMonitor - Memory metrics only")
    result = tool.execute(metric="memory")
    if psutil_available:
        print_result(result, expected_success=True)
    else:
        print_result(result, expected_success=False)
        print("(Expected failure - psutil not installed)")


def main():
    """Run all tests."""
    print("="*60)
    print("PHASE 2: SYSTEM/PERFORMANCE TOOLS TESTING")
    print("="*60)

    try:
        test_system_info()
        test_performance_monitor()

        print("\n" + "="*60)
        print("✅ SYSTEM TOOLS TESTS COMPLETE")
        print("="*60)
        print("\nSummary:")
        print("- SystemInfoTool: Tests OS, Python, disk info")
        print("- PerformanceMonitor: Tests CPU, memory, network, disk")
        print("\nThese tools work on ANY system without special hardware.")
        print("Review output above for any ❌ FAIL results.")

    except Exception as e:
        print(f"\n❌ TEST SUITE CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
