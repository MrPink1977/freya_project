"""Base agent implementation."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from freya.domain.exceptions import AgentShutdownError, AgentStartupError, AgentStateError
from freya.domain.interfaces.agent import AgentState, IAgent
from freya.domain.interfaces.message_bus import IMessageBus
from freya.domain.value_objects.event import Event
from freya.shared.logging.decorators import log_async_errors, log_async_performance
from freya.shared.logging.logger import get_logger


class BaseAgent(ABC, IAgent):
    """
    Abstract base class for all agents.
    
    Provides common functionality:
    - Lifecycle management (start/stop)
    - Event subscription
    - State tracking
    - Error handling
    """

    def __init__(
        self,
        name: str,
        message_bus: IMessageBus,
    ) -> None:
        """
        Initialize the agent.
        
        Args:
            name: Agent name (unique identifier)
            message_bus: Message bus for communication
        """
        self._name = name
        self._message_bus = message_bus
        self._state = AgentState.CREATED
        self._logger = get_logger(__name__).bind(agent=name)
        self._running = False
        self._tasks: list[asyncio.Task[None]] = []

        self._logger.info("Agent created", state=self._state.value)

    @property
    def name(self) -> str:
        """Agent name."""
        return self._name

    @property
    def state(self) -> AgentState:
        """Current agent state."""
        return self._state

    @log_async_performance(threshold_ms=1000)
    async def start(self) -> None:
        """Start the agent."""
        if self._state != AgentState.CREATED and self._state != AgentState.STOPPED:
            raise AgentStateError(
                f"Cannot start agent in state {self._state}",
                agent_name=self._name,
                current_state=self._state.value,
                expected_state=AgentState.CREATED.value,
            )

        self._state = AgentState.STARTING
        self._logger.info("Starting agent", state=self._state.value)

        try:
            # Subscribe to events
            for event_type in self.subscribes_to():
                await self._message_bus.subscribe(
                    event_type=event_type,
                    handler=self.handle_event,
                    subscriber_name=self._name,
                )

            # Run agent-specific initialization
            await self._on_start()

            self._running = True
            self._state = AgentState.RUNNING

            self._logger.info(
                "Agent started successfully",
                state=self._state.value,
                subscriptions=self.subscribes_to(),
            )

        except Exception as e:
            self._state = AgentState.ERROR
            self._logger.error(
                "Agent startup failed",
                state=self._state.value,
                error=str(e),
                exc_info=e,
            )
            raise AgentStartupError(
                f"Failed to start agent {self._name}",
                agent_name=self._name,
                cause=e,
            ) from e

    @log_async_performance(threshold_ms=2000)
    async def stop(self) -> None:
        """Stop the agent gracefully."""
        if self._state == AgentState.STOPPED:
            self._logger.warning("Agent already stopped")
            return

        self._state = AgentState.STOPPING
        self._logger.info("Stopping agent", state=self._state.value)

        try:
            self._running = False

            # Cancel all running tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

            # Run agent-specific cleanup
            await self._on_stop()

            # Unsubscribe from events
            for event_type in self.subscribes_to():
                await self._message_bus.unsubscribe(
                    event_type=event_type,
                    handler=self.handle_event,
                )

            self._state = AgentState.STOPPED
            self._logger.info("Agent stopped successfully", state=self._state.value)

        except Exception as e:
            self._state = AgentState.ERROR
            self._logger.error(
                "Agent shutdown failed",
                state=self._state.value,
                error=str(e),
                exc_info=e,
            )
            raise AgentShutdownError(
                f"Failed to stop agent {self._name}",
                agent_name=self._name,
                cause=e,
            ) from e

    @log_async_errors()
    @log_async_performance(threshold_ms=500)
    async def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.
        
        This method delegates to _handle_event_internal which must be
        implemented by subclasses.
        """
        if not self._running:
            self._logger.debug(
                "Ignoring event (agent not running)",
                event_type=event.event_type,
                event_id=event.event_id,
            )
            return

        self._logger.debug(
            "Handling event",
            event_type=event.event_type,
            event_id=event.event_id,
            source=event.source,
        )

        await self._handle_event_internal(event)

    async def publish_event(
        self,
        event_type: str,
        data: dict[str, any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """
        Publish an event to the message bus.
        
        Args:
            event_type: Type of event to publish
            data: Event data
            correlation_id: Optional correlation ID
        """
        event = Event(
            event_type=event_type,
            data=data or {},
            source=self._name,
            correlation_id=correlation_id,
        )

        await self._message_bus.publish(event)

        self._logger.debug(
            "Event published",
            event_type=event_type,
            event_id=event.event_id,
        )

    def create_task(self, coro: any) -> asyncio.Task[None]:
        """
        Create and track an async task.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Created task
        """
        task = asyncio.create_task(coro)
        self._tasks.append(task)

        # Remove task from list when done
        def cleanup(t: asyncio.Task[None]) -> None:
            if t in self._tasks:
                self._tasks.remove(t)

        task.add_done_callback(cleanup)

        return task

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    def subscribes_to(self) -> list[str]:
        """Return list of event types this agent subscribes to."""
        ...

    @abstractmethod
    async def _handle_event_internal(self, event: Event) -> None:
        """Handle an event (implemented by subclass)."""
        ...

    async def _on_start(self) -> None:
        """
        Agent-specific startup logic.
        
        Override this method to add custom initialization.
        """
        pass

    async def _on_stop(self) -> None:
        """
        Agent-specific cleanup logic.
        
        Override this method to add custom cleanup.
        """
        pass
