"""Audio Channel Manager: Intelligent routing and channel isolation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from ..core.message_bus import Message, MessageBus, MessagePriority
from ..logger import get_logger

logger = get_logger("audio_channel_manager")


class ChannelState(str, Enum):
    """Channel operational states."""

    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"
    MUTED = "muted"
    DISABLED = "disabled"


@dataclass
class ChannelActivity:
    """Track channel activity for smart routing."""

    channel_id: str
    state: ChannelState = ChannelState.IDLE
    last_wake_time: Optional[datetime] = None
    last_activity_time: Optional[datetime] = None
    wake_count: int = 0
    error_count: int = 0


@dataclass
class ChannelRoutingRule:
    """Define routing behavior for channels."""

    channel_id: str
    priority: int = 0  # Higher = more important
    auto_mute_others: bool = True  # Mute other channels when active
    allow_interruption: bool = False  # Can be interrupted by other channels
    exclusive: bool = False  # Only this channel can be active


class AudioChannelManager:
    """
    Manages audio channel routing and isolation.

    Features:
    - Smart channel prioritization (doorbell > PC)
    - Automatic channel muting/unmuting
    - Conflict resolution (multiple wake events)
    - Channel health monitoring
    - Activity-based routing decisions

    Rules:
    1. When doorbell wakes: PC mutes until response complete
    2. When PC wakes while doorbell active: queue or interrupt based on rules
    3. Only one channel speaks/listens at a time (mutex)
    4. Failed channels automatically disabled after threshold

    Message Flow:
    wake.detected(channel_id) → evaluate_routing() → mute/unmute → route_to_channel()
    speech.speech_complete → release_channel() → unmute_all()
    """

    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus

        # Channel tracking
        self.channels: dict[str, ChannelActivity] = {}
        self.rules: dict[str, ChannelRoutingRule] = {}

        # Active state
        self._active_channel: Optional[str] = None
        self._channel_lock = asyncio.Lock()

        # Configuration
        self.error_threshold = 3  # Disable channel after N errors
        self.auto_release_timeout = 60.0  # Release stuck channels after N seconds

        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Initialize channel manager and subscribe to events."""
        # Register default channels
        await self.register_channel(
            "pc",
            ChannelRoutingRule(
                channel_id="pc",
                priority=1,
                auto_mute_others=False,  # PC doesn't mute others by default
                allow_interruption=True,  # Can be interrupted by doorbell
            ),
        )

        await self.register_channel(
            "doorbell",
            ChannelRoutingRule(
                channel_id="doorbell",
                priority=10,  # Higher priority
                auto_mute_others=True,  # Mutes PC when active
                allow_interruption=False,  # Cannot be interrupted
                exclusive=True,  # Exclusive focus
            ),
        )

        # Subscribe to events (not async)
        self.message_bus.subscribe("wake.detected", self._handle_wake_detected)
        self.message_bus.subscribe("speech.speech_complete", self._handle_speech_complete)
        self.message_bus.subscribe("speech.error", self._handle_speech_error)
        self.message_bus.subscribe("channel.mute", self._handle_mute_request)
        self.message_bus.subscribe("channel.unmute", self._handle_unmute_request)

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_channels())

        logger.info("AudioChannelManager started with channels: %s", list(self.channels.keys()))

    async def stop(self) -> None:
        """Clean up resources."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("AudioChannelManager stopped")

    async def register_channel(
        self,
        channel_id: str,
        rule: ChannelRoutingRule,
    ) -> None:
        """Register a new audio channel with routing rules."""
        self.channels[channel_id] = ChannelActivity(channel_id=channel_id)
        self.rules[channel_id] = rule

        logger.info(
            "Registered channel: %s (priority=%d, exclusive=%s)",
            channel_id,
            rule.priority,
            rule.exclusive,
        )

    async def _handle_wake_detected(self, message: Message) -> None:
        """Handle wake word detection from any channel."""
        channel_id = message.payload.get("channel_id", "pc")

        if channel_id not in self.channels:
            logger.warning("Wake detected on unknown channel: %s", channel_id)
            return

        activity = self.channels[channel_id]
        _rule = self.rules[channel_id]  # noqa: F841 - Reserved for future use

        # Update activity
        activity.last_wake_time = datetime.now()
        activity.wake_count += 1

        # Check if channel is disabled
        if activity.state == ChannelState.DISABLED:
            logger.warning("Wake detected on disabled channel: %s", channel_id)
            await self._publish_routing_decision(
                channel_id,
                action="rejected",
                reason="Channel disabled",
                correlation_id=message.correlation_id,
            )
            return

        # Route to channel
        async with self._channel_lock:
            # Check if another channel is active
            if self._active_channel and self._active_channel != channel_id:
                await self._handle_channel_conflict(
                    channel_id, self._active_channel, message.correlation_id
                )
            else:
                # Activate this channel
                await self._activate_channel(channel_id, message.correlation_id)

    async def _handle_channel_conflict(
        self,
        requesting_channel: str,
        active_channel: str,
        correlation_id: Optional[str],
    ) -> None:
        """Resolve conflict when multiple channels request activation."""
        requesting_rule = self.rules[requesting_channel]
        active_rule = self.rules[active_channel]

        # Check priority
        if requesting_rule.priority > active_rule.priority:
            # Higher priority wins
            if active_rule.allow_interruption:
                logger.info(
                    "Channel %s interrupting %s (priority %d > %d)",
                    requesting_channel,
                    active_channel,
                    requesting_rule.priority,
                    active_rule.priority,
                )

                # Mute active channel
                await self._set_channel_state(active_channel, ChannelState.MUTED)

                # Activate requesting channel
                await self._activate_channel(requesting_channel, correlation_id)
            else:
                logger.warning(
                    "Channel %s cannot interrupt %s (not allowed)",
                    requesting_channel,
                    active_channel,
                )
                await self._publish_routing_decision(
                    requesting_channel,
                    action="queued",
                    reason=f"{active_channel} active and cannot be interrupted",
                    correlation_id=correlation_id,
                )
        else:
            # Lower or equal priority - queue or reject
            logger.info(
                "Channel %s queued (priority %d <= %d of active %s)",
                requesting_channel,
                requesting_rule.priority,
                active_rule.priority,
                active_channel,
            )
            await self._publish_routing_decision(
                requesting_channel,
                action="queued",
                reason=f"{active_channel} has higher/equal priority",
                correlation_id=correlation_id,
            )

    async def _activate_channel(
        self,
        channel_id: str,
        correlation_id: Optional[str],
    ) -> None:
        """Activate a channel for interaction."""
        rule = self.rules[channel_id]
        activity = self.channels[channel_id]

        # Set as active
        self._active_channel = channel_id
        activity.state = ChannelState.LISTENING
        activity.last_activity_time = datetime.now()

        # Mute other channels if required
        if rule.auto_mute_others:
            for other_id in self.channels:
                if other_id != channel_id:
                    await self._set_channel_state(other_id, ChannelState.MUTED)

        # Publish routing decision
        await self._publish_routing_decision(
            channel_id,
            action="activated",
            reason="Channel priority and availability",
            correlation_id=correlation_id,
        )

        logger.info("Activated channel: %s", channel_id)

    async def _handle_speech_complete(self, message: Message) -> None:
        """Handle speech completion - release channel."""
        channel_id = message.payload.get("channel_id", "pc")

        if channel_id == self._active_channel:
            await self._release_channel(channel_id)

    async def _release_channel(self, channel_id: str) -> None:
        """Release active channel and unmute others."""
        async with self._channel_lock:
            if self._active_channel != channel_id:
                return

            activity = self.channels[channel_id]
            activity.state = ChannelState.IDLE
            self._active_channel = None

            # Unmute all channels
            for ch_id in self.channels:
                if self.channels[ch_id].state == ChannelState.MUTED:
                    await self._set_channel_state(ch_id, ChannelState.IDLE)

            logger.info("Released channel: %s", channel_id)

    async def _handle_speech_error(self, message: Message) -> None:
        """Handle speech errors - track failures."""
        channel_id = message.payload.get("channel_id", "pc")

        if channel_id not in self.channels:
            return

        activity = self.channels[channel_id]
        activity.error_count += 1

        # Disable channel if too many errors
        if activity.error_count >= self.error_threshold:
            await self._set_channel_state(channel_id, ChannelState.DISABLED)
            logger.error(
                "Channel %s disabled after %d errors",
                channel_id,
                activity.error_count,
            )

        # Release if this was the active channel
        if self._active_channel == channel_id:
            await self._release_channel(channel_id)

    async def _handle_mute_request(self, message: Message) -> None:
        """Handle explicit mute request."""
        channel_id = message.payload.get("channel_id", "pc")

        if channel_id in self.channels:
            await self._set_channel_state(channel_id, ChannelState.MUTED)

    async def _handle_unmute_request(self, message: Message) -> None:
        """Handle explicit unmute request."""
        channel_id = message.payload.get("channel_id", "pc")

        if channel_id in self.channels:
            await self._set_channel_state(channel_id, ChannelState.IDLE)

    async def _set_channel_state(
        self,
        channel_id: str,
        state: ChannelState,
    ) -> None:
        """Update channel state and notify SpeechAgent."""
        if channel_id not in self.channels:
            return

        activity = self.channels[channel_id]
        old_state = activity.state
        activity.state = state

        # Notify SpeechAgent
        if state == ChannelState.MUTED:
            await self.message_bus.publish(
                topic="speech.mute_channel",
                payload={"channel_id": channel_id},
                sender="channel_manager",
            )
        elif state == ChannelState.IDLE and old_state == ChannelState.MUTED:
            await self.message_bus.publish(
                topic="speech.unmute_channel",
                payload={"channel_id": channel_id},
                sender="channel_manager",
            )

        logger.debug("Channel %s: %s → %s", channel_id, old_state, state)

    async def _publish_routing_decision(
        self,
        channel_id: str,
        action: str,
        reason: str,
        correlation_id: Optional[str],
    ) -> None:
        """Publish routing decision for transparency."""
        await self.message_bus.publish(
            topic="channel.routing_decision",
            payload={
                "channel_id": channel_id,
                "action": action,
                "reason": reason,
            },
            sender="channel_manager",
            priority=MessagePriority.HIGH,
            correlation_id=correlation_id,
        )

    async def _monitor_channels(self) -> None:
        """Background task to monitor channel health."""
        while True:
            try:
                await asyncio.sleep(10.0)  # Check every 10 seconds

                now = datetime.now()

                # Check for stuck channels
                if self._active_channel:
                    activity = self.channels[self._active_channel]

                    if activity.last_activity_time:
                        elapsed = (now - activity.last_activity_time).total_seconds()

                        if elapsed > self.auto_release_timeout:
                            logger.warning(
                                "Auto-releasing stuck channel %s (active for %.1fs)",
                                self._active_channel,
                                elapsed,
                            )
                            await self._release_channel(self._active_channel)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in channel monitor: %s", e)

    def get_channel_status(self) -> dict[str, dict]:
        """Get status of all channels for debugging."""
        return {
            channel_id: {
                "state": activity.state.value,
                "priority": self.rules[channel_id].priority,
                "wake_count": activity.wake_count,
                "error_count": activity.error_count,
                "last_wake": (
                    activity.last_wake_time.isoformat() if activity.last_wake_time else None
                ),
            }
            for channel_id, activity in self.channels.items()
        }
