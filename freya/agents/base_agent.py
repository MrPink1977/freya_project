"""
BASE AGENT CLASS FOR FREYA'S AGENT-BASED ARCHITECTURE.

All specialized agents inherit from BaseAgent.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from freya.core.message_bus import Message, MessageBus, MessagePriority
from freya.logger import get_logger


class AgentState(Enum):
    """Agent lifecycle states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentCapability:
    """Describes what an agent can do."""

    name: str
    description: str
    input_topics: list[str]  # Topics this agent subscribes to
    output_topics: list[str]  # Topics this agent publishes to


class BaseAgent(ABC):
    """
    Abstract base class for all Freya agents.

    Provides:
    - Message bus integration
    - Lifecycle management (init, start, stop)
    - State tracking
    - Error handling
    - Resource cleanup
    """

    def __init__(self, agent_id: str, bus: MessageBus) -> None:
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier for this agent
            bus: Message bus for communication
        """
        self.agent_id = agent_id
        self.bus = bus
        self.state = AgentState.CREATED
        self.logger = get_logger(f"agent.{agent_id}")
        self._tasks: list[asyncio.Task] = []

        self.logger.info(f"Agent {agent_id} created")

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize agent resources (models, connections, etc.).

        Called once before agent starts processing.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[AgentCapability]:
        """
        Return list of agent capabilities.

        Used for capability discovery and routing.
        Must be implemented by subclasses.
        """
        pass

    async def start(self) -> None:
        """
        Start agent - subscribes to topics and begins processing.

        Calls initialize() if not already initialized.
        """
        if self.state == AgentState.READY:
            self.logger.warning(f"Agent {self.agent_id} already started")
            return

        try:
            self.state = AgentState.INITIALIZING
            await self.initialize()

            # Subscribe to input topics
            capabilities = self.get_capabilities()
            for capability in capabilities:
                for topic in capability.input_topics:
                    self.bus.subscribe(topic, self._handle_message)
                    self.logger.debug(f"Subscribed to topic: {topic}")

            self.state = AgentState.READY
            self.logger.info(f"Agent {self.agent_id} started and ready")

        except Exception as exc:
            self.state = AgentState.ERROR
            self.logger.exception(f"Failed to start agent {self.agent_id}: {exc}")
            raise

    async def stop(self) -> None:
        """
        Stop agent - cleanup resources and cancel tasks.
        """
        self.logger.info(f"Stopping agent {self.agent_id}")
        self.state = AgentState.STOPPED

        # Cancel all running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._tasks.clear()

        # Cleanup agent-specific resources
        try:
            await self.cleanup()
        except Exception as exc:
            self.logger.exception(f"Error during cleanup: {exc}")

        self.logger.info(f"Agent {self.agent_id} stopped")

    async def cleanup(self) -> None:
        """
        Cleanup agent resources.

        Override in subclasses to cleanup models, connections, etc.
        """
        pass

    async def _handle_message(self, message: Message) -> None:
        """
        Internal message handler - routes to process_message with error handling.

        Args:
            message: Message from bus
        """
        if self.state != AgentState.READY:
            self.logger.warning(
                f"Agent {self.agent_id} not ready (state: {self.state.value}), "
                f"ignoring message on topic: {message.topic}"
            )
            return

        try:
            prev_state = self.state
            self.state = AgentState.BUSY

            await self.process_message(message)

            self.state = prev_state

        except Exception as exc:
            self.logger.exception(
                f"Error processing message on topic {message.topic}: {exc}"
            )
            self.state = AgentState.ERROR
            # Publish error event
            await self.publish_error(message, exc)

    @abstractmethod
    async def process_message(self, message: Message) -> None:
        """
        Process incoming message.

        Must be implemented by subclasses.

        Args:
            message: Message to process
        """
        pass

    async def publish(
        self,
        topic: str,
        payload: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
    ) -> None:
        """
        Publish message to bus.

        Args:
            topic: Topic to publish to
            payload: Message payload
            priority: Message priority
            correlation_id: Optional correlation ID for tracking
        """
        await self.bus.publish(
            topic=topic,
            payload=payload,
            sender=self.agent_id,
            priority=priority,
            correlation_id=correlation_id,
        )
        self.logger.debug(f"Published to {topic}")

    async def publish_error(self, original_message: Message, error: Exception) -> None:
        """
        Publish error event to bus.

        Args:
            original_message: Message that caused the error
            error: Exception that occurred
        """
        await self.publish(
            topic=f"agent.{self.agent_id}.error",
            payload={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "original_topic": original_message.topic,
                "original_payload": original_message.payload,
            },
            priority=MessagePriority.HIGH,
            correlation_id=original_message.correlation_id,
        )

    def create_task(self, coro) -> asyncio.Task:
        """
        Create and track async task.

        Args:
            coro: Coroutine to run

        Returns:
            Created task
        """
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        task.add_done_callback(self._tasks.remove)
        return task

    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status.

        Returns:
            Status dictionary
        """
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "active_tasks": len([t for t in self._tasks if not t.done()]),
            "capabilities": [c.name for c in self.get_capabilities()],
        }
