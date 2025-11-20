"""
Test ChromaMemoryStore functionality.

Run with: python tests/test_chroma_memory.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from freya.memory import ChromaMemoryStore


def test_store_and_retrieve():
    """Test basic store and retrieval."""
    print("\n=== Testing ChromaMemoryStore ===\n")

    # Create temp memory store
    store = ChromaMemoryStore(db_path="data/test_chroma_memory")

    print("Storing memories...")
    store.store_memory(content="My name is Tommy", role="user", importance=5)
    store.store_memory(content="I love pizza", role="user", importance=3)
    store.store_memory(content="I hate Mondays", role="user", importance=2)
    store.store_memory(
        content="I work as a software engineer", role="user", importance=4
    )
    store.store_memory(content="The weather is nice today", role="user", importance=1)

    print(f"Stored 5 memories\n")

    # Test similarity search
    print("Testing similarity search:\n")

    # Query 1: Should find "My name is Tommy"
    results = store.find_similar_memories("What's my name?", limit=3)
    print(f"Query: 'What's my name?'")
    for r in results:
        print(f"  - {r.content} (score: {r.score:.3f})")
    assert any("Tommy" in r.content for r in results), "Should find name"
    print()

    # Query 2: Should find "I love pizza"
    results = store.find_similar_memories("What food do I like?", limit=3)
    print(f"Query: 'What food do I like?'")
    for r in results:
        print(f"  - {r.content} (score: {r.score:.3f})")
    assert any("pizza" in r.content for r in results), "Should find pizza"
    print()

    # Query 3: Should find "I work as a software engineer"
    results = store.find_similar_memories("What's my job?", limit=3)
    print(f"Query: 'What's my job?'")
    for r in results:
        print(f"  - {r.content} (score: {r.score:.3f})")
    assert any("engineer" in r.content for r in results), "Should find job"
    print()

    # Test stats
    stats = store.get_stats()
    print(f"Stats: {stats}")
    assert stats["total_memories"] == 5

    print("\n[SUCCESS] ChromaMemoryStore basic tests passed!")


def test_facts():
    """Test fact storage and retrieval."""
    print("\n=== Testing Fact Storage ===\n")

    store = ChromaMemoryStore(db_path="data/test_chroma_memory")

    print("Storing facts...")
    store.store_fact(category="name", key="first_name", value="Tommy", confidence=1.0)
    store.store_fact(
        category="preference", key="favorite_color", value="blue", confidence=0.9
    )
    store.store_fact(
        category="preference", key="favorite_food", value="pizza", confidence=1.0
    )

    # Query facts
    print("\nQuerying facts:\n")

    results = store.query_facts("What's my favorite color?", limit=2)
    print(f"Query: 'What's my favorite color?'")
    for f in results:
        print(f"  - {f.category}/{f.key}: {f.value} (confidence: {f.confidence})")
    assert any(f.value == "blue" for f in results)
    print()

    # Get all preferences
    prefs = store.get_all_facts(category="preference")
    print(f"All preferences: {len(prefs)} facts")
    for f in prefs:
        print(f"  - {f.key}: {f.value}")

    print("\n[SUCCESS] Fact storage tests passed!")


def test_performance():
    """Test with larger dataset."""
    print("\n=== Testing Performance ===\n")

    store = ChromaMemoryStore(db_path="data/test_chroma_memory")

    print("Adding 50 memories...")
    for i in range(50):
        store.store_memory(
            content=f"Memory number {i} with some random content", role="user"
        )

    stats = store.get_stats()
    print(f"Total memories: {stats['total_memories']}")

    print("Searching...")
    results = store.find_similar_memories("random content", limit=5)
    print(f"Found {len(results)} matches")

    print("\n[SUCCESS] Performance test passed!")


def cleanup():
    """Clean up test data."""
    import shutil

    test_dir = Path("data/test_chroma_memory")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("\n[CLEANUP] Removed test data")


if __name__ == "__main__":
    try:
        test_store_and_retrieve()
        test_facts()
        test_performance()

        print("\n" + "=" * 50)
        print("[SUCCESS] All ChromaMemoryStore tests passed!")
        print("=" * 50)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        cleanup()
