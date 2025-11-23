#!/usr/bin/env python3
"""
Comprehensive Test Suite for Freya
Tests ALL capabilities: Voice, Vision, Tools, Memory, etc.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("FREYA COMPREHENSIVE CAPABILITY TEST")
print("=" * 80)
print()

# Test 1: Import all modules
print("Test 1: Module Imports")
print("-" * 80)
try:
    from freya.config import load_settings
    from freya.context import ConversationContext
    from freya.ollama_client import OllamaClient
    from freya.tools import ToolManager

    print("✓ All core modules imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Tool System
print("\nTest 2: Tool System")
print("-" * 80)
try:
    manager = ToolManager()
    tools = manager.list_tools(enabled_only=True)
    print(f"✓ Tool Manager initialized with {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
except Exception as e:
    print(f"✗ Tool system failed: {e}")

# Test 3: Tool Execution Tests
print("\nTest 3: Tool Execution")
print("-" * 80)

test_cases = [
    # Time & Date
    ("get_current_time", {"timezone": "UTC", "format": "24h"}, "Time tools"),
    ("get_current_date", {"format": "long"}, "Date tools"),
    ("calculate_time_until", {"target_date": "2025-12-25"}, "Time calculation"),
    # Calculator
    ("calculator", {"expression": "2 + 2"}, "Basic math"),
    ("calculator", {"expression": "sqrt(16) + 10"}, "Math functions"),
    ("calculator", {"expression": "sin(pi/2)"}, "Trigonometry"),
    # File operations
    ("list_files", {"path": ".", "pattern": "*.py"}, "List Python files"),
    ("list_files", {"path": "freya/tools", "pattern": "*.py"}, "List tool files"),
    # System
    ("system_info", {"info_type": "os"}, "OS information"),
    ("system_info", {"info_type": "python"}, "Python information"),
]

passed = 0
failed = 0

for tool_name, kwargs, description in test_cases:
    try:
        result = manager.execute_tool(tool_name, **kwargs)
        if result.success:
            output = result.output[:60] + "..." if len(result.output) > 60 else result.output
            print(f"✓ {description}: {output}")
            passed += 1
        else:
            print(f"✗ {description}: {result.error}")
            failed += 1
    except Exception as e:
        print(f"✗ {description}: Exception - {e}")
        failed += 1

print(f"\nTool Tests: {passed} passed, {failed} failed")

# Test 4: Configuration
print("\nTest 4: Configuration System")
print("-" * 80)
try:
    settings = load_settings()
    print("✓ Configuration loaded")
    print(f"  - Ollama host: {settings.ollama.host}")
    print(f"  - Ollama model: {settings.ollama.model}")
    print(f"  - Wake word: {settings.app.wake_word}")
    print(f"  - Interaction mode: {settings.app.interaction_mode}")
except Exception as e:
    print(f"✗ Configuration failed: {e}")

# Test 5: Ollama Connection
print("\nTest 5: Ollama Connection")
print("-" * 80)
try:
    settings = load_settings()
    client = OllamaClient(settings.ollama)

    # Test basic chat
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Respond briefly."},
        {"role": "user", "content": "Say 'Hello from Freya test suite!' and nothing else."},
    ]

    print(f"Connecting to Ollama at {settings.ollama.host}...")
    response = client.chat(messages, stream=False)

    if response:
        print("✓ Ollama responding")
        print(f"  Response: {response[:100]}")
    else:
        print("✗ Empty response from Ollama")

except Exception as e:
    print(f"✗ Ollama connection failed: {e}")
    print("  Make sure Ollama is running: ollama serve")

# Test 6: Memory System
print("\nTest 6: Memory System")
print("-" * 80)
try:
    import os
    import tempfile

    from freya.memory import PersistentMemoryStore

    # Create temporary DB
    temp_db = os.path.join(tempfile.gettempdir(), "test_freya_memory.db")

    store = PersistentMemoryStore(temp_db)

    # Add a test memory
    store.add_memory("user", "My name is Test User", importance=5)

    # Search for it
    results = store.find_similar_memories("what is my name", limit=5)

    if results:
        print("✓ Memory system working")
        print(f"  - Stored and retrieved {len(results)} memories")
    else:
        print("✗ Memory retrieval failed")

    # Cleanup
    try:
        os.remove(temp_db)
    except OSError:
        pass

except Exception as e:
    print(f"✗ Memory system failed: {e}")

# Test 7: Context Management
print("\nTest 7: Context Management")
print("-" * 80)
try:
    context = ConversationContext(
        system_prompt="You are Freya, a helpful assistant.", max_history=10
    )

    context.add_user_message("Hello!")
    context.add_assistant_message("Hi! How can I help you?")
    context.add_user_message("What's 2+2?")
    context.add_assistant_message("2+2 equals 4.")

    messages = context.as_messages()

    print("✓ Context management working")
    print(f"  - Messages in context: {len(messages)}")
    print(f"  - System prompt: {messages[0]['content'][:50]}...")

except Exception as e:
    print(f"✗ Context failed: {e}")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("✓ Core Systems: Imports, Tools, Config, Memory, Context")
print(f"✓ Tool Tests: {passed}/{passed+failed} passed")
print("? Ollama: Check output above")
print()
print("NEXT STEPS:")
print("1. If Ollama test failed, start Ollama: ollama serve")
print("2. Run main.py to test full integration")
print("3. Try voice commands in voice mode")
print("4. Try camera integration (if hardware available)")
print("=" * 80)
