"""TTS engine check."""

from __future__ import annotations

from . import BaseSystemCheck, CheckResult, CheckStatus


class TTSCheck(BaseSystemCheck):
    """Check TTS engine availability."""

    def __init__(self, engine: str = "piper"):
        super().__init__(
            name="TTS Engine",
            description=f"Check {engine} TTS engine",
            required=True,
        )
        self.engine = engine.lower()

    async def run(self) -> CheckResult:
        """Check TTS engine."""
        if self.engine == "piper":
            return await self._check_piper()
        elif self.engine == "elevenlabs":
            return await self._check_elevenlabs()
        else:
            return CheckResult(
                status=CheckStatus.WARNING,
                message=f"Unknown engine: {self.engine}",
            )

    async def _check_piper(self) -> CheckResult:
        """Check Piper TTS."""
        try:
            import piper
        except ImportError:
            try:
                import piper_tts
            except ImportError:
                return CheckResult(
                    status=CheckStatus.FAILED,
                    message="piper-tts not installed",
                    fix_suggestion="pip install piper-tts",
                )

        return CheckResult(
            status=CheckStatus.PASSED,
            message="Piper TTS available",
            details="Local TTS engine",
        )

    async def _check_elevenlabs(self) -> CheckResult:
        """Check ElevenLabs TTS."""
        try:
            import elevenlabs
        except ImportError:
            return CheckResult(
                status=CheckStatus.FAILED,
                message="elevenlabs not installed",
                fix_suggestion="pip install elevenlabs",
            )

        # Check for API key
        import os

        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return CheckResult(
                status=CheckStatus.WARNING,
                message="ElevenLabs library installed",
                details="ELEVENLABS_API_KEY not set",
                fix_suggestion="Set ELEVENLABS_API_KEY environment variable",
            )

        return CheckResult(
            status=CheckStatus.PASSED,
            message="ElevenLabs TTS ready",
            details="API key configured",
        )
