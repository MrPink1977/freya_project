"""
Test MemoryAgent functionality.

Run with: python tests/test_memory_agent.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from freya.agents.memory_agent import MemoryAgent
from freya.core import MessageBus
from freya.memory import ChromaMemoryStore


async def test_memory_storage():
    """Test async memory storage."""
    print("\n=== Testing MemoryAgent Storage ===\n")

    bus = MessageBus()
    await bus.start()

    store = ChromaMemoryStore(db_path="data/test_memory_agent")
    agent = MemoryAgent("memory", bus, store)
    await agent.start()

    # Track results
    stored = []

    async def stored_handler(message):
        stored.append(message)
        print(f"[STORED] Memory: {message.payload['memory_id']}")

    bus.subscribe("memory.stored", stored_handler)

    # Store some memories
    print("Storing memories...\n")
    test_memories = [
        "My name is Tommy",
        "I love pizza",
        "I work as a software engineer",
    ]

    for text in test_memories:
        await bus.publish(
            topic="memory.store",
            payload={"content": text, "role": "user", "importance": 3},
            sender="test",
        )

    await asyncio.sleep(0.5)

    assert len(stored) == 3, f"Expected 3 stored, got {len(stored)}"
    print(f"[OK] Stored {len(stored)} memories\n")

    await agent.stop()
    await bus.stop()


async def test_memory_query():
    """Test memory retrieval."""
    print("\n=== Testing Memory Query ===\n")

    bus = MessageBus()
    await bus.start()

    store = ChromaMemoryStore(db_path="data/test_memory_agent")
    agent = MemoryAgent("memory", bus, store)
    await agent.start()

    results = []

    async def results_handler(message):
        results.append(message)
        print(f"[RESULTS] Found {message.payload['count']} memories")
        for r in message.payload["results"]:
            print(f"  - {r['content']} (score: {r['score']:.3f})")

    bus.subscribe("memory.results", results_handler)

    # Query memories
    queries = [
        "What's my name?",
        "What food do I like?",
        "What's my job?",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        results.clear()

        await bus.publish(
            topic="memory.query",
            payload={"query": query, "limit": 3},
            sender="test",
        )

        await asyncio.sleep(0.3)

        assert len(results) == 1, "Should get one result message"
        assert results[0].payload["count"] > 0, f"Should find memories for '{query}'"
        print()

    await agent.stop()
    await bus.stop()


async def test_fact_extraction():
    """Test automatic fact extraction."""
    print("\n=== Testing Fact Extraction ===\n")

    bus = MessageBus()
    await bus.start()

    store = ChromaMemoryStore(db_path="data/test_memory_agent")
    agent = MemoryAgent("memory", bus, store, auto_extract_facts=True)
    await agent.start()

    facts_stored = []

    async def fact_stored_handler(message):
        facts_stored.append(message)
        payload = message.payload
        print(f"[FACT] {payload['category']}/{payload['key']} = {payload['value']}")

    bus.subscribe("memory.fact.stored", fact_stored_handler)

    # Test fact extraction patterns
    print("Testing fact extraction...\n")
    test_statements = [
        "My name is Alice",
        "My favorite color is blue",
        "I love chocolate",
        "My birthday is January 15th",
    ]

    for statement in test_statements:
        print(f"Statement: '{statement}'")
        facts_stored.clear()

        await bus.publish(
            topic="memory.store",
            payload={"content": statement, "role": "user"},
            sender="test",
        )

        await asyncio.sleep(0.3)

        # Should extract fact (name, preference, or birthday)
        assert len(facts_stored) > 0, f"Should extract fact from '{statement}'"
        print()

    await agent.stop()
    await bus.stop()


async def test_fact_query():
    """Test fact querying."""
    print("\n=== Testing Fact Query ===\n")

    bus = MessageBus()
    await bus.start()

    store = ChromaMemoryStore(db_path="data/test_memory_agent")
    agent = MemoryAgent("memory", bus, store)
    await agent.start()

    results = []

    async def fact_results_handler(message):
        results.append(message)
        print(f"[FACTS] Found {message.payload['count']} facts")
        for f in message.payload["results"]:
            print(f"  - {f['category']}/{f['key']}: {f['value']}")

    bus.subscribe("memory.fact.results", fact_results_handler)

    # Query facts
    print("Querying: 'What's my name?'\n")
    await bus.publish(
        topic="memory.fact.query",
        payload={"query": "name", "limit": 3},
        sender="test",
    )

    await asyncio.sleep(0.3)

    assert len(results) == 1
    assert results[0].payload["count"] > 0, "Should find name fact"

    await agent.stop()
    await bus.stop()


async def main():
    """Run all tests."""
    try:
        await test_memory_storage()
        await test_memory_query()
        await test_fact_extraction()
        await test_fact_query()

        print("\n" + "=" * 50)
        print("[SUCCESS] All MemoryAgent tests passed!")
        print("=" * 50)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        # Cleanup
        import shutil

        test_dir = Path("data/test_memory_agent")
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("\n[CLEANUP] Removed test data")


if __name__ == "__main__":
    asyncio.run(main())
