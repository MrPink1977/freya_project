"""
Test ToolExecutorAgent functionality.

Run with: python tests/test_tool_executor_agent.py
"""

import asyncio

from freya.agents.tool_executor_agent import ToolExecutorAgent
from freya.core import MessageBus
from freya.tools.manager import ToolManager


async def test_tool_detection():
    """Test tool detection and execution."""
    print("\n=== Testing ToolExecutorAgent ===\n")

    bus = MessageBus()
    await bus.start()

    tool_manager = ToolManager()
    agent = ToolExecutorAgent("tool_executor", bus, tool_manager)
    await agent.start()

    # Track results
    results = []

    async def result_handler(message):
        results.append(message)
        print(f"[RESULT] Tool: {message.payload['tool_name']}")
        print(f"  Success: {message.payload['success']}")
        print(f"  Output: {message.payload['output'][:100]}...")
        print()

    async def not_found_handler(message):
        results.append(message)
        print(f"[NO TOOL] Query: {message.payload['query']}")
        print()

    bus.subscribe("tool.result", result_handler)
    bus.subscribe("tool.not_found", not_found_handler)

    # Test queries
    test_cases = [
        ("what time is it?", "get_current_time"),
        ("what's today's date?", "get_current_date"),
        ("calculate 25 + 17", "calculator"),
        ("system info", "system_info"),
        ("cpu usage", "performance_monitor"),
        ("hello how are you?", None),  # No tool
    ]

    print("Testing tool detection:\n")
    for query, expected_tool in test_cases:
        print(f"Query: '{query}'")
        results.clear()

        await bus.publish(
            topic="user.query",
            payload={"text": query},
            sender="test",
            correlation_id=f"test-{len(results)}",
        )

        # Wait for processing
        await asyncio.sleep(0.2)

        if expected_tool:
            assert len(results) == 1
            assert results[0].topic == "tool.result"
            assert results[0].payload["tool_name"] == expected_tool
            print(f"  [OK] Detected: {expected_tool}\n")
        else:
            assert len(results) == 1
            assert results[0].topic == "tool.not_found"
            print("  [OK] No tool detected\n")

    await agent.stop()
    await bus.stop()

    print("=" * 50)
    print("[SUCCESS] All tool detection tests passed!")
    print("=" * 50)


async def test_tool_execution():
    """Test actual tool execution with real results."""
    print("\n=== Testing Tool Execution ===\n")

    bus = MessageBus()
    await bus.start()

    tool_manager = ToolManager()
    agent = ToolExecutorAgent("tool_executor", bus, tool_manager)
    await agent.start()

    results = []

    async def result_handler(message):
        results.append(message)

    bus.subscribe("tool.result", result_handler)

    # Test time tool
    print("Testing: What time is it in Tokyo?")
    await bus.publish(
        topic="user.query", payload={"text": "what time is it in Tokyo?"}, sender="test"
    )
    await asyncio.sleep(0.2)

    assert len(results) == 1
    assert results[0].payload["success"] is True
    assert "Tokyo" in results[0].payload["output"] or ":" in results[0].payload["output"]
    print(f"  Result: {results[0].payload['output']}\n")

    # Test calculator
    results.clear()
    print("Testing: Calculate 100 * 25")
    await bus.publish(topic="user.query", payload={"text": "calculate 100 * 25"}, sender="test")
    await asyncio.sleep(0.2)

    assert len(results) == 1
    assert results[0].payload["success"] is True
    assert "2500" in results[0].payload["output"]
    print(f"  Result: {results[0].payload['output']}\n")

    await agent.stop()
    await bus.stop()

    print("[SUCCESS] Tool execution tests passed!")


async def main():
    """Run all tests."""
    try:
        await test_tool_detection()
        await test_tool_execution()

        print("\n" + "=" * 50)
        print("[SUCCESS] All ToolExecutorAgent tests passed!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n[FAILED] Assertion error: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
