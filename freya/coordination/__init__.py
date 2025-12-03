"""Coordination module - agent orchestration and lifecycle management."""

from .orchestration_coordinator import OrchestrationCoordinator, create_coordinator_from_config
from .orchestrator_mcp import MCPOrchestrator

__all__ = ["OrchestrationCoordinator", "create_coordinator_from_config", "MCPOrchestrator"]
