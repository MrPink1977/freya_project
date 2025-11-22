"""Agent interface protocol."""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

from freya.domain.value_objects.event import Event


class AgentState(str, Enum):
    """Agent lifecycle states."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@runtime_checkable
class IAgent(Protocol):
    """
    Interface for all agents in the system.
    
    Agents are independent components that:
    - Subscribe to events via the message bus
    - Process events asynchronously
    - Publish new events
    - Manage their own lifecycle
    """

    @property
    def name(self) -> str:
        """Agent name (unique identifier)."""
        ...

    @property
    def state(self) -> AgentState:
        """Current agent state."""
        ...

    async def start(self) -> None:
        """
        Start the agent.
        
        Raises:
            AgentStartupError: If agent fails to start
        """
        ...

    async def stop(self) -> None:
        """
        Stop the agent gracefully.
        
        Raises:
            AgentShutdownError: If agent fails to stop
        """
        ...

    async def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.
        
        Args:
            event: Event to process
            
        Raises:
            AgentMessageError: If event handling fails
        """
        ...

    def subscribes_to(self) -> list[str]:
        """
        Get list of event types this agent subscribes to.
        
        Returns:
            List of event type names
        """
        ...
