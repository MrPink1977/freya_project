"""Tests for memory query reliability and empty result handling."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from freya.agents.memory_agent import MemoryAgent
from freya.core.message_bus import Message, MessageBus
from freya.memory.memory_store import ChromaMemoryStore, Fact


class TestMemoryEmptyResults:
    """Test empty result handling in memory queries."""

    def test_empty_query_returns_empty_list(self):
        """Empty query string returns empty list."""
        with patch('freya.memory.chromadb'):
            store = ChromaMemoryStore()

            results = store.query_facts("")
            assert results == []

            results = store.query_facts("   ")
            assert results == []

    def test_no_matching_facts_returns_empty_list(self):
        """Query with no matches returns empty list."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            # Mock ChromaDB client
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            # Mock empty query results
            mock_collection.query.return_value = {
                "ids": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }

            store = ChromaMemoryStore()
            results = store.query_facts("nonexistent query")

            assert results == []

    def test_relevance_filtering_returns_empty_when_all_low_relevance(self):
        """Returns empty list when all results below relevance threshold."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            # Mock results with high distance (low relevance)
            mock_collection.query.return_value = {
                "ids": [["fact1", "fact2"]],
                "metadatas": [[
                    {"category": "test", "key": "key1", "value": "value1", "confidence": 1.0},
                    {"category": "test", "key": "key2", "value": "value2", "confidence": 1.0}
                ]],
                "distances": [[1.8, 1.9]]  # Very high distance = low relevance
            }

            store = ChromaMemoryStore()
            results = store.query_facts("test query", min_relevance_score=0.5)

            # Both results should be filtered out due to low relevance
            assert results == []

    def test_relevance_filtering_includes_high_relevance(self):
        """Includes results above relevance threshold."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            # Mock results with mixed relevance
            mock_collection.query.return_value = {
                "ids": [["fact1", "fact2", "fact3"]],
                "metadatas": [[
                    {"category": "test", "key": "key1", "value": "good match", "confidence": 1.0},
                    {"category": "test", "key": "key2", "value": "poor match", "confidence": 1.0},
                    {"category": "test", "key": "key3", "value": "decent match", "confidence": 1.0}
                ]],
                "distances": [[0.2, 1.8, 0.8]]  # Good, poor, decent relevance
            }

            store = ChromaMemoryStore()
            results = store.query_facts("test query", min_relevance_score=0.5)

            # Should include fact1 (0.9 relevance) and fact3 (0.6 relevance)
            # Should exclude fact2 (0.1 relevance)
            assert len(results) == 2
            assert results[0].value == "good match"
            assert results[1].value == "decent match"

    def test_custom_min_relevance_score(self):
        """Custom min_relevance_score is respected."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            mock_collection.query.return_value = {
                "ids": [["fact1", "fact2"]],
                "metadatas": [[
                    {"category": "test", "key": "key1", "value": "value1", "confidence": 1.0},
                    {"category": "test", "key": "key2", "value": "value2", "confidence": 1.0}
                ]],
                "distances": [[0.5, 1.0]]  # 0.75 and 0.5 relevance
            }

            store = ChromaMemoryStore()

            # With threshold 0.6, should include only first
            results = store.query_facts("test", min_relevance_score=0.6)
            assert len(results) == 1

            # With threshold 0.4, should include both
            results = store.query_facts("test", min_relevance_score=0.4)
            assert len(results) == 2


class TestMemoryAgentEmptyResults:
    """Test empty result handling in memory agent."""

    @pytest.mark.asyncio
    async def test_empty_results_include_helpful_message(self):
        """Empty query results include helpful message."""
        mock_bus = Mock(spec=MessageBus)

        with patch('freya.agents.memory_agent.ChromaMemoryStore') as mock_store_class:
            mock_store = Mock()
            mock_store.query_facts.return_value = []  # Empty results
            mock_store_class.return_value = mock_store

            agent = MemoryAgent(
                agent_id="test_memory",
                bus=mock_bus,
                memory_store=mock_store
            )

            await agent.initialize()

            message = Message(
                topic="memory.fact.query",
                payload={"query": "nonexistent", "category": None, "limit": 3},
                correlation_id="test-123"
            )

            await agent._handle_fact_query(message)

            # Should publish results with helpful message
            mock_bus.publish.assert_called_once()
            call_args = mock_bus.publish.call_args

            assert call_args[1]["payload"]["count"] == 0
            assert call_args[1]["payload"]["results"] == []
            assert "No memories found" in call_args[1]["payload"]["message"]

    @pytest.mark.asyncio
    async def test_query_with_results_no_empty_message(self):
        """Query with results doesn't include empty message."""
        mock_bus = Mock(spec=MessageBus)

        with patch('freya.agents.memory_agent.ChromaMemoryStore') as mock_store_class:
            mock_store = Mock()
            mock_fact = Fact(
                id="fact1",
                category="test",
                key="key1",
                value="value1",
                confidence=1.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            mock_store.query_facts.return_value = [mock_fact]
            mock_store_class.return_value = mock_store

            agent = MemoryAgent(
                agent_id="test_memory",
                bus=mock_bus,
                memory_store=mock_store
            )

            await agent.initialize()

            message = Message(
                topic="memory.fact.query",
                payload={"query": "existing", "category": None, "limit": 3},
                correlation_id="test-123"
            )

            await agent._handle_fact_query(message)

            call_args = mock_bus.publish.call_args

            assert call_args[1]["payload"]["count"] == 1
            assert len(call_args[1]["payload"]["results"]) == 1
            assert "message" not in call_args[1]["payload"]


class TestMemoryQueryLogging:
    """Test logging for memory queries."""

    def test_empty_query_logs_debug(self):
        """Empty query logs debug message."""
        with patch('freya.memory.chromadb'), \
             patch('freya.memory.logger') as mock_logger:

            store = ChromaMemoryStore()
            _results = store.query_facts("")  # noqa: F841

            mock_logger.debug.assert_called()
            assert "Empty query" in str(mock_logger.debug.call_args)

    def test_no_results_logs_debug(self):
        """No results logs debug message."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            mock_collection.query.return_value = {
                "ids": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }

            with patch('freya.memory.logger') as mock_logger:
                store = ChromaMemoryStore()
                _results = store.query_facts("test query")  # noqa: F841

                # Should log that no facts were found
                debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
                assert any("No facts found" in call for call in debug_calls)

    def test_low_relevance_filtering_logs_debug(self):
        """Filtering low-relevance results logs debug message."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            mock_collection.query.return_value = {
                "ids": [["fact1"]],
                "metadatas": [[
                    {"category": "test", "key": "key1", "value": "value1", "confidence": 1.0}
                ]],
                "distances": [[1.9]]  # Very low relevance
            }

            with patch('freya.memory.logger') as mock_logger:
                store = ChromaMemoryStore()
                _results = store.query_facts("test", min_relevance_score=0.5)  # noqa: F841

                # Should log filtering
                debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
                assert any("Filtering out fact" in call for call in debug_calls)


class TestMemoryRelevanceScoring:
    """Test relevance scoring for memory results."""

    def test_perfect_match_high_relevance(self):
        """Perfect match (distance 0) has relevance 1.0."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            mock_collection.query.return_value = {
                "ids": [["fact1"]],
                "metadatas": [[
                    {"category": "test", "key": "key1", "value": "perfect", "confidence": 1.0}
                ]],
                "distances": [[0.0]]  # Perfect match
            }

            store = ChromaMemoryStore()
            results = store.query_facts("test", min_relevance_score=0.99)

            # Should include perfect match
            assert len(results) == 1

    def test_opposite_match_low_relevance(self):
        """Opposite match (distance 2.0) has relevance 0.0."""
        with patch('freya.memory.chromadb') as mock_chromadb:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.Client.return_value = mock_client

            mock_collection.query.return_value = {
                "ids": [["fact1"]],
                "metadatas": [[
                    {"category": "test", "key": "key1", "value": "opposite", "confidence": 1.0}
                ]],
                "distances": [[2.0]]  # Opposite match
            }

            store = ChromaMemoryStore()
            results = store.query_facts("test", min_relevance_score=0.1)

            # Should exclude opposite match
            assert len(results) == 0
