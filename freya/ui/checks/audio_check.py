"""Audio device checks."""

from __future__ import annotations

from . import BaseSystemCheck, CheckResult, CheckStatus


class MicrophoneCheck(BaseSystemCheck):
    """Check microphone access."""

    def __init__(self):
        super().__init__(
            name="Microphone",
            description="Check microphone device access",
            required=True,
        )

    async def run(self) -> CheckResult:
        """Check microphone."""
        try:
            import sounddevice as sd
        except ImportError:
            return CheckResult(
                status=CheckStatus.FAILED,
                message="sounddevice not installed",
                fix_suggestion="pip install sounddevice",
            )

        try:
            # Try to open default input device
            with sd.InputStream(channels=1, samplerate=16000, blocksize=512):
                pass

            # Get device info
            default_input = sd.query_devices(kind="input")
            device_name = default_input.get("name", "Unknown")

            return CheckResult(
                status=CheckStatus.PASSED,
                message="Microphone accessible",
                details=f"Device: {device_name}",
            )

        except Exception as e:
            return CheckResult(
                status=CheckStatus.FAILED,
                message=f"Cannot access microphone: {type(e).__name__}",
                details=str(e),
                fix_suggestion="Check microphone permissions",
            )


class SpeakerCheck(BaseSystemCheck):
    """Check speaker/audio output access."""

    def __init__(self):
        super().__init__(
            name="Audio Output",
            description="Check speaker/audio output device",
            required=False,
        )

    async def run(self) -> CheckResult:
        """Check audio output."""
        try:
            import sounddevice as sd
        except ImportError:
            return CheckResult(
                status=CheckStatus.FAILED,
                message="sounddevice not installed",
                fix_suggestion="pip install sounddevice",
            )

        try:
            # Get default output device
            default_output = sd.query_devices(kind="output")
            device_name = default_output.get("name", "Unknown")

            return CheckResult(
                status=CheckStatus.PASSED,
                message="Audio output available",
                details=f"Device: {device_name}",
            )

        except Exception as e:
            return CheckResult(
                status=CheckStatus.WARNING,
                message=f"Cannot detect audio output: {type(e).__name__}",
                details=str(e),
            )
