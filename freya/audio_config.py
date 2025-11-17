"""Utilities for loading multi-channel audio configuration."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

try:  # pragma: no cover - optional dependency is validated via tests
    import yaml
except ImportError:  # pragma: no cover - handled at runtime
    yaml = None  # type: ignore[assignment]

from .multi_channel_coordinator import ChannelConfig, ChannelType

logger = logging.getLogger(__name__)


def _expand_env(value: object) -> object:
    """Expand environment variables inside string values."""

    if isinstance(value, str):
        expanded = os.path.expandvars(value)
        return expanded
    return value


def _validate_credential_security(field_name: str, value: object) -> None:
    """Warn if credentials appear to be stored as plaintext instead of environment variables."""

    if not isinstance(value, str):
        return

    # Check if the value looks like an environment variable reference
    # Valid patterns: ${VAR}, $VAR, or empty/placeholder values
    if not value:
        return

    is_env_var = (
        value.startswith("${") and value.endswith("}") or  # ${VAR} syntax
        value.startswith("$") and not value.startswith("${") or  # $VAR syntax
        value in ("your_password_here", "your_username_here", "PLACEHOLDER")  # Placeholders
    )

    if not is_env_var:
        logger.warning(
            "Security: %s appears to contain a literal credential instead of an environment variable. "
            "Consider using ${ENV_VAR} syntax and storing credentials in a .env file.",
            field_name
        )


def _parse_channel(channel_id: str, raw: dict) -> ChannelConfig:
    """Create a :class:`ChannelConfig` from the YAML mapping."""

    if not isinstance(raw, dict):
        raise ValueError(f"Channel '{channel_id}' must map to a dictionary")

    type_str = str(raw.get("type", "system"))
    channel_type = ChannelType.from_str(type_str)

    enabled = bool(raw.get("enabled", True))

    if channel_type == ChannelType.SYSTEM:
        device_index = raw.get("device_index")
        config = ChannelConfig(
            channel_id=channel_id,
            channel_type=channel_type,
            enabled=enabled,
            device_index=device_index if device_index is not None else None,
            description=raw.get("description"),
        )
    elif channel_type == ChannelType.REOLINK:
        # Validate credential security before expansion
        username_raw = raw.get("username")
        password_raw = raw.get("password")
        _validate_credential_security(f"Channel '{channel_id}' username", username_raw)
        _validate_credential_security(f"Channel '{channel_id}' password", password_raw)

        config = ChannelConfig(
            channel_id=channel_id,
            channel_type=channel_type,
            enabled=enabled,
            ip=_expand_env(raw.get("ip")),
            rtsp_port=int(raw.get("rtsp_port", 554)),
            username=_expand_env(username_raw),
            password=_expand_env(password_raw),
            description=raw.get("description"),
        )
    else:  # pragma: no cover - ChannelType exhaustive
        raise ValueError(f"Unsupported channel type {channel_type}")

    config.validate()
    return config


def load_channel_configs(config_path: str | Path) -> List[ChannelConfig]:
    """Load channel configuration entries from ``config_path``."""

    if yaml is None:
        raise RuntimeError("PyYAML is required to load audio channel configuration")

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    logger.info("Loading channel configs from %s", path)

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    audio_section = data.get("audio", {}) if isinstance(data, dict) else {}
    channels = audio_section.get("channels", {}) if isinstance(audio_section, dict) else {}

    if not channels:
        logger.warning("No channels defined in configuration")
        return []

    configs: List[ChannelConfig] = []
    for channel_id, raw in channels.items():
        try:
            config = _parse_channel(channel_id, raw)
        except Exception as exc:
            logger.error("Error loading config for channel %s: %s", channel_id, exc)
            continue
        configs.append(config)
        logger.info(
            "Loaded config for channel %s (%s)", channel_id, config.channel_type.value
        )

    return configs


def create_example_config(output_path: str | Path = "audio_config.yaml") -> Path:
    """Create an example multi-channel configuration YAML file."""

    if yaml is None:
        raise RuntimeError("PyYAML is required to write audio channel configuration")

    example = {
        "audio": {
            "channels": {
                "primary": {
                    "type": "system",
                    "enabled": True,
                    "device_index": None,
                },
                "camera_front_door": {
                    "type": "reolink",
                    "enabled": False,
                    "ip": "192.168.1.100",
                    "rtsp_port": 554,
                    "username": "${REOLINK_CAM_USER}",
                    "password": "${REOLINK_CAM_PASS}",
                    "description": "Front door camera with 2-way audio",
                },
            }
        }
    }

    path = Path(output_path)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(example, handle, default_flow_style=False, sort_keys=False)

    logger.info("Created example config at %s", path)
    return path


__all__ = ["ChannelConfig", "ChannelType", "create_example_config", "load_channel_configs"]
