#!/usr/bin/env python3
"""
Phase 2 Testing: File Operations

Tests all file tools (list_files, read_file, write_file) with:
- Normal operations
- Security validations
- Error handling
- Edge cases
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Direct import to avoid config loading
import importlib.util
spec = importlib.util.spec_from_file_location(
    "file_tools",
    Path(__file__).parent / "freya" / "tools" / "file_tools.py"
)
file_tools = importlib.util.module_from_spec(spec)

# Also need base module
spec_base = importlib.util.spec_from_file_location(
    "base",
    Path(__file__).parent / "freya" / "tools" / "base.py"
)
base_module = importlib.util.module_from_spec(spec_base)
sys.modules['freya.tools.base'] = base_module
spec_base.loader.exec_module(base_module)

# Now load file_tools
spec.loader.exec_module(file_tools)

ListFilesTool = file_tools.ListFilesTool
ReadFileTool = file_tools.ReadFileTool
WriteFileTool = file_tools.WriteFileTool

# Test directories
TEST_DATA_DIR = Path.cwd() / "data" / "test_file_tools"
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)


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
        print(f"Output:\n{result.output[:500]}")  # Limit output
    if result.error:
        print(f"Error: {result.error}")
    if result.metadata:
        print(f"Metadata: {result.metadata}")


def test_list_files():
    """Test ListFilesTool."""
    print_test("ListFilesTool - List files in test directory")

    # Create some test files
    (TEST_DATA_DIR / "test1.txt").write_text("Test file 1")
    (TEST_DATA_DIR / "test2.py").write_text("print('hello')")
    (TEST_DATA_DIR / "subdir").mkdir(exist_ok=True)
    (TEST_DATA_DIR / "subdir" / "nested.txt").write_text("Nested file")

    tool = ListFilesTool()

    # Test 1: List files in test directory
    result = tool.execute(path=str(TEST_DATA_DIR))
    print_result(result, expected_success=True)

    # Test 2: List with pattern
    print_test("ListFilesTool - Pattern matching (*.txt)")
    result = tool.execute(path=str(TEST_DATA_DIR), pattern="*.txt")
    print_result(result, expected_success=True)

    # Test 3: Recursive listing
    print_test("ListFilesTool - Recursive listing")
    result = tool.execute(path=str(TEST_DATA_DIR), recursive=True)
    print_result(result, expected_success=True)

    # Test 4: Invalid path (security test)
    print_test("ListFilesTool - Security: Path traversal attempt")
    result = tool.execute(path="/etc/passwd")
    print_result(result, expected_success=False)

    # Test 5: Non-existent path
    print_test("ListFilesTool - Error: Non-existent directory")
    result = tool.execute(path=str(TEST_DATA_DIR / "nonexistent"))
    print_result(result, expected_success=False)


def test_read_file():
    """Test ReadFileTool."""
    print_test("ReadFileTool - Read text file")

    # Create test file
    test_file = TEST_DATA_DIR / "read_test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n")

    tool = ReadFileTool()

    # Test 1: Read text file
    result = tool.execute(path=str(test_file))
    print_result(result, expected_success=True)

    # Test 2: Read with line limit
    print_test("ReadFileTool - Read with max_lines=2")
    result = tool.execute(path=str(test_file), max_lines=2)
    print_result(result, expected_success=True)

    # Test 3: Non-existent file
    print_test("ReadFileTool - Error: Non-existent file")
    result = tool.execute(path=str(TEST_DATA_DIR / "nonexistent.txt"))
    print_result(result, expected_success=False)

    # Test 4: Security test - path traversal
    print_test("ReadFileTool - Security: Path traversal attempt")
    result = tool.execute(path="/etc/passwd")
    print_result(result, expected_success=False)

    # Test 5: Binary file rejection
    print_test("ReadFileTool - Security: Binary file rejection")
    binary_file = TEST_DATA_DIR / "binary.png"
    binary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake png data")
    result = tool.execute(path=str(binary_file))
    print_result(result, expected_success=False)


def test_write_file():
    """Test WriteFileTool."""
    print_test("WriteFileTool - Write new file")

    tool = WriteFileTool()

    # Test 1: Write new file
    write_path = TEST_DATA_DIR / "write_test.txt"
    if write_path.exists():
        write_path.unlink()

    result = tool.execute(path=str(write_path), content="Hello, Freya!")
    print_result(result, expected_success=True)

    # Verify content
    if write_path.exists():
        content = write_path.read_text()
        print(f"✅ File created with content: {content!r}")
    else:
        print("❌ File was not created")

    # Test 2: Overwrite file
    print_test("WriteFileTool - Overwrite existing file")
    result = tool.execute(path=str(write_path), content="Overwritten content")
    print_result(result, expected_success=True)

    if write_path.exists():
        content = write_path.read_text()
        if content == "Overwritten content":
            print("✅ File correctly overwritten")
        else:
            print(f"❌ Content mismatch: {content!r}")

    # Test 3: Append mode
    print_test("WriteFileTool - Append to file")
    result = tool.execute(path=str(write_path), content="\nAppended line", append=True)
    print_result(result, expected_success=True)

    if write_path.exists():
        content = write_path.read_text()
        if "\nAppended line" in content:
            print("✅ Content correctly appended")
        else:
            print(f"❌ Append failed: {content!r}")

    # Test 4: Security test - path traversal
    print_test("WriteFileTool - Security: Path traversal attempt")
    result = tool.execute(path="/tmp/evil.txt", content="Should fail")
    print_result(result, expected_success=False)

    # Test 5: Create file with parent directories
    print_test("WriteFileTool - Create file with new directories")
    nested_path = TEST_DATA_DIR / "new_dir" / "subdir" / "file.txt"
    result = tool.execute(path=str(nested_path), content="Nested file")
    print_result(result, expected_success=True)

    if nested_path.exists():
        print("✅ Parent directories created automatically")

    # Test 6: Content size limit (simulate - don't actually write 11MB)
    print_test("WriteFileTool - Security: Content size validation")
    large_content = "x" * (11 * 1024 * 1024)  # 11 MB
    result = tool.execute(path=str(TEST_DATA_DIR / "large.txt"), content=large_content)
    print_result(result, expected_success=False)


def test_integration():
    """Integration test: List, Read, Write together."""
    print_test("INTEGRATION: Write → List → Read")

    # Write a file
    write_tool = WriteFileTool()
    test_file = TEST_DATA_DIR / "integration_test.txt"
    content = "Integration test content\nLine 2\nLine 3"

    write_result = write_tool.execute(path=str(test_file), content=content)
    print("Step 1: Write file")
    print_result(write_result, expected_success=True)

    # List to find it
    list_tool = ListFilesTool()
    list_result = list_tool.execute(path=str(TEST_DATA_DIR), pattern="integration_*.txt")
    print("\nStep 2: List files")
    print_result(list_result, expected_success=True)

    # Read it back
    read_tool = ReadFileTool()
    read_result = read_tool.execute(path=str(test_file))
    print("\nStep 3: Read file back")
    print_result(read_result, expected_success=True)

    # Verify content matches
    if read_result.success and read_result.output == content:
        print("\n✅ INTEGRATION TEST PASSED: Content round-trip successful")
    else:
        print("\n❌ INTEGRATION TEST FAILED: Content mismatch")


def main():
    """Run all tests."""
    print("="*60)
    print("PHASE 2: FILE TOOLS TESTING")
    print("="*60)
    print(f"Test directory: {TEST_DATA_DIR}")

    try:
        test_list_files()
        test_read_file()
        test_write_file()
        test_integration()

        print("\n" + "="*60)
        print("✅ ALL FILE TOOL TESTS COMPLETE")
        print("="*60)
        print(f"\nTest files location: {TEST_DATA_DIR}")
        print("Review the output above for any ❌ FAIL results.")

    except Exception as e:
        print(f"\n❌ TEST SUITE CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
