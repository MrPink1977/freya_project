"""Query builder for constructing complex memory queries."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class QueryBuilder:
    """
    Builder pattern for constructing memory queries.
    
    Provides a fluent interface for building complex queries.
    """

    def __init__(self) -> None:
        """Initialize query builder."""
        self._query_text: str = ""
        self._limit: int = 10
        self._similarity_threshold: float = 0.7
        self._metadata_filters: dict[str, Any] = {}
        self._time_range: tuple[datetime, datetime] | None = None

    def reset(self) -> QueryBuilder:
        """Reset the builder to initial state."""
        self._query_text = ""
        self._limit = 10
        self._similarity_threshold = 0.7
        self._metadata_filters = {}
        self._time_range = None
        return self

    def with_text(self, text: str) -> QueryBuilder:
        """
        Set query text.
        
        Args:
            text: Query text for semantic search
            
        Returns:
            Self for chaining
        """
        self._query_text = text
        return self

    def with_limit(self, limit: int) -> QueryBuilder:
        """
        Set result limit.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            Self for chaining
        """
        self._limit = limit
        return self

    def with_similarity_threshold(self, threshold: float) -> QueryBuilder:
        """
        Set similarity threshold.
        
        Args:
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            Self for chaining
        """
        self._similarity_threshold = threshold
        return self

    def with_metadata_filter(self, key: str, value: Any) -> QueryBuilder:
        """
        Add metadata filter.
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Returns:
            Self for chaining
        """
        self._metadata_filters[key] = value
        return self

    def with_time_range(
        self,
        start: datetime,
        end: datetime,
    ) -> QueryBuilder:
        """
        Set time range filter.
        
        Args:
            start: Start datetime
            end: End datetime
            
        Returns:
            Self for chaining
        """
        self._time_range = (start, end)
        return self

    def build(self) -> dict[str, Any]:
        """
        Build the query dictionary.
        
        Returns:
            Query parameters dictionary
        """
        query = {
            "query_text": self._query_text,
            "limit": self._limit,
            "similarity_threshold": self._similarity_threshold,
        }

        if self._metadata_filters:
            query["metadata_filters"] = self._metadata_filters

        if self._time_range:
            query["time_range"] = self._time_range

        return query

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"QueryBuilder("
            f"text={self._query_text!r}, "
            f"limit={self._limit}, "
            f"threshold={self._similarity_threshold}, "
            f"filters={self._metadata_filters})"
        )
