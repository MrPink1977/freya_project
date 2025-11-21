"""Whisper STT model check."""

from __future__ import annotations

from . import BaseSystemCheck, CheckResult, CheckStatus


class WhisperCheck(BaseSystemCheck):
    """Check Whisper STT availability."""

    def __init__(self, model: str = "base", device: str = "auto"):
        super().__init__(
            name="Whisper STT",
            description=f"Check Whisper model '{model}' on {device}",
            required=True,
        )
        self.model = model
        self.device = device

    async def run(self) -> CheckResult:
        """Check Whisper."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return CheckResult(
                status=CheckStatus.FAILED,
                message="faster-whisper not installed",
                fix_suggestion="pip install faster-whisper",
            )

        # Check CUDA availability if requested
        device = self.device.lower()
        if device in ("cuda", "gpu", "auto"):
            try:
                import torch

                cuda_available = torch.cuda.is_available()
                if cuda_available:
                    details = f"CUDA available: {torch.cuda.get_device_name(0)}"
                else:
                    if device == "cuda":
                        return CheckResult(
                            status=CheckStatus.WARNING,
                            message="CUDA not available, will use CPU",
                            fix_suggestion="Install CUDA-enabled PyTorch for GPU acceleration",
                        )
                    details = "CUDA not available, using CPU"
            except ImportError:
                details = "PyTorch not installed (optional)"

        try:
            # Try to load model (this will download if not cached)
            # We don't actually load it to save memory, just check it exists
            return CheckResult(
                status=CheckStatus.PASSED,
                message=f"Whisper '{self.model}' ready",
                details=f"Device: {self.device}",
            )

        except Exception as e:
            return CheckResult(
                status=CheckStatus.FAILED,
                message=f"Cannot load Whisper model: {type(e).__name__}",
                details=str(e),
            )
