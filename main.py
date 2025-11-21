"""
Freya - JARVIS-style AI Assistant with Agent Architecture

Multi-modal AI assistant with:
- Voice and text interaction
- Agent-based architecture with MessageBus
- Multi-channel audio (PC + Reolink doorbell)
- Tool execution (9 tools: time, calculator, files, web, system)
- Semantic memory with ChromaDB
- Smart model escalation (llama3.2  dolphin-mixtral)
- Facial recognition (future)
"""

import argparse
import asyncio
import os
import sys
from dataclasses import replace
from enum import Enum, auto
from pathlib import Path

from freya.config import load_settings
from freya.coordination.orchestration_coordinator import create_coordinator_from_config
from freya.logger import get_logger

logger = get_logger("main")


class StartupMode(Enum):
    """Startup mode for the application."""
    NORMAL = auto()
    DIAGNOSTIC = auto()


def _parse_mode(mode_str: str) -> StartupMode:
    """Parse startup mode string to enum."""
    if mode_str.lower() == "diagnostic":
        return StartupMode.DIAGNOSTIC
    return StartupMode.NORMAL


def _select_startup_mode(config) -> StartupMode:
    """Select startup mode based on config and user input."""
    default_mode = _parse_mode(config.startup_mode)

    # If not interactive or prompting disabled, use config default
    if not os.isatty(0) or not config.prompt_for_mode:
        return default_mode

    # Interactive mode selection
    try:
        response = input("Select mode (n=normal, d=diagnostic): ").strip().lower()
        if response == "d":
            return StartupMode.DIAGNOSTIC
        return StartupMode.NORMAL
    except (EOFError, KeyboardInterrupt):
        return default_mode


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Freya - Voice-first AI assistant with agent architecture"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="Path to configuration file (default: config/default.yaml)",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["voice", "text"],
        help="Interaction mode: voice or text (overrides config)",
    )

    parser.add_argument(
        "--engine",
        type=str,
        choices=["piper", "elevenlabs"],
        help="TTS engine: piper (local) or elevenlabs (cloud, requires API key)",
    )

    parser.add_argument(
        "--model",
        type=str,
        help="Default LLM model (e.g., llama3.2:3b, dolphin-mixtral:8x7b)",
    )

    parser.add_argument(
        "--no-agents",
        action="store_true",
        help="Use legacy orchestrator instead of agent architecture",
    )

    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Run startup diagnostics",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check system dependencies and exit",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    try:
        config = load_settings(config_path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Override config with CLI args (using dataclasses.replace for frozen dataclasses)
    if args.mode:
        config = replace(config, app=replace(config.app, interaction_mode=args.mode))
    if args.engine:
        config = replace(config, tts=replace(config.tts, engine=args.engine))
    if args.model:
        config = replace(config, ollama=replace(config.ollama, model=args.model))
    if args.diagnostic:
        config = replace(config, app=replace(config.app, startup_mode="diagnostic"))

    # Run system check if requested
    if args.check:
        from freya.system_check import run_system_check

        run_system_check(config)
        return

    # Banner
    print("\n" + "=" * 60)
    print("  FREYA - AI Assistant")
    print("  Agent Architecture | Multi-Channel Audio | Tool Integration")
    print("=" * 60)
    print(f"  Mode: {config.app.interaction_mode.upper()}")
    print(f"  TTS Engine: {config.tts.engine}")
    print(f"  LLM Model: {config.ollama.model}")
    print(f"  Wake Word: '{config.app.wake_word}'")
    print("=" * 60 + "\n")

    # Run diagnostics if requested
    if config.app.startup_mode == "diagnostic":
        logger.info("Running startup diagnostics...")
        from freya.system_check import run_system_check

        run_system_check(config)

        if config.app.prompt_for_mode:
            response = input("\nContinue to voice mode? (y/n): ").strip().lower()
            if response != "y":
                logger.info("Exiting after diagnostics")
                return

    # Check for legacy mode
    if args.no_agents:
        logger.warning("Legacy orchestrator mode not implemented - using agents")
        # Future: could fall back to old orchestrator.py here

    # Create coordinator with agent architecture
    print("[DEBUG] main: Creating coordinator...")
    try:
        coordinator = create_coordinator_from_config(config)
        print("[DEBUG] main: Coordinator created")
    except Exception as e:
        logger.error(f"Failed to create coordinator: {e}")
        logger.exception(e)
        sys.exit(1)

    # Run coordinator
    print("[DEBUG] main: Running coordinator...")
    try:
        await coordinator.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Runtime error: {e}")
        logger.exception(e)
        sys.exit(1)

    logger.info("Freya shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Ctrl+C] Exiting Freya. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
