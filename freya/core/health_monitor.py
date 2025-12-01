"""
HEALTH MONITORING FOR AGENTS.

Provides simple 30s heartbeat monitoring for debugging.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from freya.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentHealth:
    """Health status for an agent."""

    agent_id: str
    last_heartbeat: float
    state: str
    message_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """Check if agent is healthy (heartbeat within 30s)."""
        return (time.time() - self.last_heartbeat) < 30.0

    @property
    def seconds_since_heartbeat(self) -> float:
        """Get seconds since last heartbeat."""
        return time.time() - self.last_heartbeat


class HealthMonitor:
    """
    Simple health monitoring system.

    Features:
    - 30s heartbeat tracking
    - Agent health status
    - Message/error counting
    - Async monitoring loop
    """

    def __init__(self, heartbeat_interval: float = 30.0) -> None:
        """
        Initialize health monitor.

        Args:
            heartbeat_interval: Expected heartbeat interval in seconds (default 30s)
        """
        self.heartbeat_interval = heartbeat_interval
        self._agents: Dict[str, AgentHealth] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        logger.info(f"HealthMonitor initialized (heartbeat_interval={heartbeat_interval}s)")

    async def start(self) -> None:
        """Start health monitoring loop."""
        if self._running:
            logger.warning("HealthMonitor already running")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("HealthMonitor started")

    async def stop(self) -> None:
        """Stop health monitoring."""
        if not self._running:
            return

        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("HealthMonitor stopped")

    async def register_agent(
        self,
        agent_id: str,
        state: str = "created",
        metadata: Optional[Dict[str, any]] = None,
    ) -> None:
        """
        Register an agent for health monitoring.

        Args:
            agent_id: Agent identifier
            state: Initial agent state
            metadata: Optional metadata about the agent
        """
        async with self._lock:
            self._agents[agent_id] = AgentHealth(
                agent_id=agent_id,
                last_heartbeat=time.time(),
                state=state,
                metadata=metadata or {},
            )
            logger.debug(f"Registered agent: {agent_id}")

    async def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from health monitoring.

        Args:
            agent_id: Agent identifier
        """
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.debug(f"Unregistered agent: {agent_id}")

    async def heartbeat(
        self,
        agent_id: str,
        state: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None,
    ) -> None:
        """
        Record heartbeat from agent.

        Args:
            agent_id: Agent identifier
            state: Optional state update
            metadata: Optional metadata update
        """
        # Check if agent exists (without holding lock for auto-register)
        async with self._lock:
            agent_exists = agent_id in self._agents

        # Auto-register if not found (outside lock to avoid deadlock)
        if not agent_exists:
            await self.register_agent(agent_id, state=state or "unknown", metadata=metadata)
            return

        # Update existing agent
        async with self._lock:
            health = self._agents[agent_id]
            health.last_heartbeat = time.time()

            if state:
                health.state = state

            if metadata:
                health.metadata.update(metadata)

            logger.debug(f"Heartbeat from {agent_id} (state={health.state})")

    async def record_message(self, agent_id: str) -> None:
        """
        Record that agent processed a message.

        Args:
            agent_id: Agent identifier
        """
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].message_count += 1

    async def record_error(self, agent_id: str, error: str) -> None:
        """
        Record an error from agent.

        Args:
            agent_id: Agent identifier
            error: Error message
        """
        async with self._lock:
            if agent_id in self._agents:
                health = self._agents[agent_id]
                health.error_count += 1
                health.last_error = error
                logger.warning(f"Error recorded for {agent_id}: {error}")

    async def get_health(self, agent_id: str) -> Optional[AgentHealth]:
        """
        Get health status for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentHealth or None if not registered
        """
        async with self._lock:
            return self._agents.get(agent_id)

    async def get_all_health(self) -> Dict[str, AgentHealth]:
        """
        Get health status for all agents.

        Returns:
            Dictionary of agent_id -> AgentHealth
        """
        async with self._lock:
            return dict(self._agents)

    async def get_unhealthy_agents(self) -> Dict[str, AgentHealth]:
        """
        Get all unhealthy agents (no heartbeat in 30s).

        Returns:
            Dictionary of unhealthy agents
        """
        async with self._lock:
            return {
                agent_id: health
                for agent_id, health in self._agents.items()
                if not health.is_healthy
            }

    async def _monitor_loop(self) -> None:
        """Main monitoring loop - checks for unhealthy agents."""
        logger.debug("Health monitor loop started")

        while self._running:
            try:
                # Check for unhealthy agents
                unhealthy = await self.get_unhealthy_agents()

                if unhealthy:
                    for agent_id, health in unhealthy.items():
                        logger.warning(
                            f"Agent {agent_id} is UNHEALTHY - "
                            f"no heartbeat for {health.seconds_since_heartbeat:.1f}s "
                            f"(state={health.state}, errors={health.error_count})"
                        )

                # Sleep for monitoring interval
                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                logger.debug("Health monitor loop cancelled")
                break
            except Exception as exc:
                logger.exception(f"Error in health monitor loop: {exc}")
                await asyncio.sleep(5)  # Brief pause on error

    async def get_stats(self) -> Dict[str, any]:
        """
        Get health monitor statistics.

        Returns:
            Dictionary with stats
        """
        async with self._lock:
            healthy_count = sum(1 for h in self._agents.values() if h.is_healthy)
            unhealthy_count = len(self._agents) - healthy_count
            total_messages = sum(h.message_count for h in self._agents.values())
            total_errors = sum(h.error_count for h in self._agents.values())

            return {
                "running": self._running,
                "total_agents": len(self._agents),
                "healthy_agents": healthy_count,
                "unhealthy_agents": unhealthy_count,
                "total_messages": total_messages,
                "total_errors": total_errors,
                "heartbeat_interval": self.heartbeat_interval,
            }
