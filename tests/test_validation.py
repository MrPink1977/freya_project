"""Quick validation test for agent architecture."""

import sys
import asyncio

# Test imports
print("Testing imports...")
try:
    from freya.core.message_bus import MessageBus
    print("  ✓ MessageBus")
except Exception as e:
    print(f"  ✗ MessageBus: {e}")
    sys.exit(1)

try:
    from freya.agents.base_agent import BaseAgent
    print("  ✓ BaseAgent")
except Exception as e:
    print(f"  ✗ BaseAgent: {e}")
    sys.exit(1)

try:
    from freya.agents.dialog_agent import DialogAgent
    print("  ✓ DialogAgent")
except Exception as e:
    print(f"  ✗ DialogAgent: {e}")
    sys.exit(1)

try:
    from freya.agents.memory_agent import MemoryAgent
    print("  ✓ MemoryAgent")
except Exception as e:
    print(f"  ✗ MemoryAgent: {e}")
    sys.exit(1)

try:
    from freya.agents.tool_executor_agent import ToolExecutorAgent
    print("  ✓ ToolExecutorAgent")
except Exception as e:
    print(f"  ✗ ToolExecutorAgent: {e}")
    sys.exit(1)

try:
    from freya.agents.wake_word_agent import WakeWordAgent
    print("  ✓ WakeWordAgent")
except Exception as e:
    print(f"  ✗ WakeWordAgent: {e}")
    sys.exit(1)

try:
    from freya.coordination.orchestration_coordinator import OrchestrationCoordinator
    print("  ✓ OrchestrationCoordinator")
except Exception as e:
    print(f"  ✗ OrchestrationCoordinator: {e}")
    sys.exit(1)

print("\n✓ All imports successful!")

# Test basic message bus
print("\nTesting MessageBus...")
async def test_bus():
    bus = MessageBus()
    received = []
    
    async def handler(msg):
        received.append(msg)
    
    bus.subscribe("test.topic", handler)
    
    from freya.core.message_bus import Message, MessagePriority
    await bus.publish(Message(
        topic="test.topic",
        payload={"data": "test"},
        priority=MessagePriority.NORMAL
    ))
    
    await asyncio.sleep(0.1)
    
    if received:
        print("  ✓ MessageBus pub/sub working")
        return True
    else:
        print("  ✗ MessageBus pub/sub failed")
        return False

if asyncio.run(test_bus()):
    print("\n✓✓✓ VALIDATION PASSED ✓✓✓")
    print("\nAgent architecture is functional!")
    sys.exit(0)
else:
    print("\n✗ VALIDATION FAILED")
    sys.exit(1)
