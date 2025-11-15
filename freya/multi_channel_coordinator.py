"""Data models for Freya's multi-channel audio coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChannelType(str, Enum):
    """Supported audio channel types."""

    SYSTEM = "system"
    REOLINK = "reolink"

    @classmethod
    def from_str(cls, raw: str) -> "ChannelType":
        """Return a :class:`ChannelType` from ``raw`` ignoring case."""

        try:
            normalised = raw.strip().lower()
        except AttributeError as exc:  # pragma: no cover - defensive
            raise ValueError("channel type must be a string") from exc

        for member in cls:
            if member.value == normalised:
                return member
        raise ValueError(f"unsupported channel type: {raw}")


@dataclass(frozen=True)
class ChannelConfig:
    """Configuration for a single audio channel."""

    channel_id: str
    channel_type: ChannelType
    enabled: bool = True
    # System channel options
    device_index: Optional[int] = None
    # Reolink channel options
    ip: Optional[str] = None
    rtsp_port: int = 554
    username: Optional[str] = None
    password: Optional[str] = None
    # Misc metadata for future routing
    description: Optional[str] = field(default=None)

    def validate(self) -> None:
        """Validate the configuration and raise :class:`ValueError` on issues."""

        if not self.channel_id:
            raise ValueError("channel_id cannot be empty")

        if self.channel_type == ChannelType.REOLINK:
            missing = [
                name
                for name, value in (
                    ("ip", self.ip),
                    ("username", self.username),
                    ("password", self.password),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    f"Reolink channel '{self.channel_id}' missing required field(s): "
                    + ", ".join(missing)
                )
            if self.rtsp_port <= 0:
                raise ValueError(
                    f"Reolink channel '{self.channel_id}' must have a positive rtsp_port"
                )

        if self.channel_type == ChannelType.SYSTEM and self.device_index is not None:
            if not isinstance(self.device_index, int):
                raise ValueError(
                    f"System channel '{self.channel_id}' device_index must be an integer or None"
                )


__all__ = ["ChannelConfig", "ChannelType"]