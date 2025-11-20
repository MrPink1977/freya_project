"""Coordination module - agent orchestration and lifecycle management."""

from .orchestration_coordinator import OrchestrationCoordinator, create_coordinator_from_config

__all__ = ["OrchestrationCoordinator", "create_coordinator_from_config"]
