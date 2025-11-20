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
from freya.core.health_monitor import HealthMonitor
from freya.exceptions import (
    AgentCleanupError,
    AgentInitializationError,
    AgentMessageError,
)
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

    def __init__(
        self,
        agent_id: str,
        bus: MessageBus,
        health_monitor: Optional[HealthMonitor] = None,
    ) -> None:
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier for this agent
            bus: Message bus for communication
            health_monitor: Optional health monitor for heartbeat tracking
        """
        self.agent_id = agent_id
        self.bus = bus
        self.health_monitor = health_monitor
        self.state = AgentState.CREATED
        self.logger = get_logger(f"agent.{agent_id}")
        self._tasks: list[asyncio.Task] = []
        self._heartbeat_task: Optional[asyncio.Task] = None

        self.logger.info(f"Agent {agent_id} created")

        # Register with health monitor if available
        if self.health_monitor:
            asyncio.create_task(
                self.health_monitor.register_agent(agent_id, state=self.state.value)
            )

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

            # Start heartbeat task if health monitor is available
            if self.health_monitor:
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            self.logger.info(f"Agent {self.agent_id} started and ready")

        except Exception as exc:
            self.state = AgentState.ERROR
            self.logger.exception(f"Failed to start agent {self.agent_id}: {exc}")
            
            # Record error in health monitor
            if self.health_monitor:
                await self.health_monitor.record_error(self.agent_id, str(exc))
            
            raise AgentInitializationError(
                f"Agent {self.agent_id} failed to initialize: {exc}",
                agent_id=self.agent_id,
                error=str(exc),
            )

    async def stop(self) -> None:
        """
        Stop agent - cleanup resources and cancel tasks.
        """
        self.logger.info(f"Stopping agent {self.agent_id}")
        self.state = AgentState.STOPPED

        # Cancel heartbeat task
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Cancel all running tasks with proper exception handling
        if self._tasks:
            self.logger.debug(f"Cancelling {len(self._tasks)} tasks for {self.agent_id}")
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete cancellation
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

        # Cleanup agent-specific resources
        try:
            await self.cleanup()
        except Exception as exc:
            # Log but don't raise - we're shutting down anyway
            self.logger.error(
                f"Agent {self.agent_id} cleanup failed: {exc}",
                exc_info=True,
            )

        # Unregister from health monitor
        if self.health_monitor:
            await self.health_monitor.unregister_agent(self.agent_id)

        self.logger.info(f"Agent {self.agent_id} stopped")

    def _cleanup_completed_tasks(self) -> None:
        """
        Remove completed tasks from the task set (prevents memory leak).
        
        Called on-demand when task count exceeds threshold to balance
        memory usage vs cleanup overhead.
        """
        if len(self._tasks) > 100:  # Cleanup threshold
            before_count = len(self._tasks)
            self._tasks = {task for task in self._tasks if not task.done()}
            cleaned = before_count - len(self._tasks)
            if cleaned > 0:
                self.logger.debug(f"Cleaned up {cleaned} completed tasks for {self.agent_id}")

    async def cleanup(self) -> None:
        """
        Cleanup agent resources.

        Override in subclasses to cleanup models, connections, etc.
        """
        pass

    async def restart(self) -> None:
        """
        Manually restart agent.

        Useful for recovering from errors or applying configuration changes.
        """
        self.logger.info(f"Restarting agent {self.agent_id}")
        
        try:
            # Stop the agent
            await self.stop()
            
            # Brief pause to ensure cleanup
            await asyncio.sleep(0.5)
            
            # Restart the agent
            await self.start()
            
            self.logger.info(f"Agent {self.agent_id} restarted successfully")
            
        except Exception as exc:
            self.logger.exception(f"Failed to restart agent {self.agent_id}: {exc}")
            self.state = AgentState.ERROR
            
            if self.health_monitor:
                await self.health_monitor.record_error(self.agent_id, f"Restart failed: {exc}")
            
            raise

    async def _heartbeat_loop(self) -> None:
        """
        Heartbeat loop - sends periodic health updates.

        Runs every 30 seconds while agent is active.
        """
        self.logger.debug(f"Heartbeat loop started for {self.agent_id}")
        
        while self.state != AgentState.STOPPED:
            try:
                if self.health_monitor:
                    await self.health_monitor.heartbeat(
                        agent_id=self.agent_id,
                        state=self.state.value,
                        metadata=self._get_heartbeat_metadata(),
                    )
                
                # Wait 30 seconds before next heartbeat
                await asyncio.sleep(30.0)
                
            except asyncio.CancelledError:
                self.logger.debug(f"Heartbeat loop cancelled for {self.agent_id}")
                break
            except Exception as exc:
                self.logger.error(f"Error in heartbeat loop: {exc}")
                await asyncio.sleep(5)  # Brief pause on error

    def _get_heartbeat_metadata(self) -> Dict[str, Any]:
        """
        Get metadata to include in heartbeat.

        Override in subclasses to add custom metadata.

        Returns:
            Dictionary of metadata
        """
        return {
            "active_tasks": len([t for t in self._tasks if not t.done()]),
            "total_tasks": len(self._tasks),
        }

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
            
            # Record successful message processing
            if self.health_monitor:
                await self.health_monitor.record_message(self.agent_id)

        except Exception as exc:
            self.logger.exception(f"Error processing message on topic {message.topic}: {exc}")
            self.state = AgentState.ERROR
            
            # Record error in health monitor
            if self.health_monitor:
                await self.health_monitor.record_error(self.agent_id, str(exc))
            
            # Publish error event
            error = AgentMessageError(
                f"Agent {self.agent_id} failed to process message on {message.topic}: {exc}",
                agent_id=self.agent_id,
                topic=message.topic,
                error=str(exc),
            )
            await self.publish_error(message, error)

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
        
        # Cleanup completed tasks periodically to prevent memory leak
        self._cleanup_completed_tasks()

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
