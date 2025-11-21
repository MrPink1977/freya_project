"""Ollama connection and model check."""

from __future__ import annotations

from typing import Optional

from . import BaseSystemCheck, CheckResult, CheckStatus


class OllamaCheck(BaseSystemCheck):
    """Check Ollama connection and model availability."""

    def __init__(self, host: str, model: Optional[str] = None):
        super().__init__(
            name="Ollama Connection",
            description=f"Check connection to {host}",
            required=True,
        )
        self.host = host.rstrip("/")
        self.model = model

    async def run(self) -> CheckResult:
        """Check Ollama connection and model."""
        try:
            import httpx
        except ImportError:
            return CheckResult(
                status=CheckStatus.FAILED,
                message="httpx library not installed",
                fix_suggestion="pip install httpx",
            )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")

            if response.status_code != 200:
                return CheckResult(
                    status=CheckStatus.FAILED,
                    message=f"HTTP {response.status_code}",
                    fix_suggestion="Ensure Ollama is running: 'ollama serve'",
                )

            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]

            if not model_names:
                return CheckResult(
                    status=CheckStatus.WARNING,
                    message="No models available",
                    fix_suggestion="Pull a model: 'ollama pull llama3.2:3b'",
                )

            # Check specific model if requested
            if self.model:
                if self.model not in model_names:
                    available = ", ".join(model_names[:3])
                    return CheckResult(
                        status=CheckStatus.WARNING,
                        message=f"Model '{self.model}' not found",
                        details=f"Available: {available}...",
                        fix_suggestion=f"Pull model: 'ollama pull {self.model}'",
                    )

                return CheckResult(
                    status=CheckStatus.PASSED,
                    message=f"Model '{self.model}' ready",
                    details=f"Total models: {len(model_names)}",
                )

            return CheckResult(
                status=CheckStatus.PASSED,
                message=f"{len(model_names)} model(s) available",
                details=f"Models: {', '.join(model_names[:3])}...",
            )

        except httpx.ConnectError:
            return CheckResult(
                status=CheckStatus.FAILED,
                message="Cannot connect to Ollama",
                fix_suggestion="Start Ollama: 'ollama serve'",
            )
        except Exception as e:
            return CheckResult(
                status=CheckStatus.FAILED,
                message=f"Check failed: {type(e).__name__}",
                details=str(e),
            )
