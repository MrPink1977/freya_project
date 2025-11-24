"""System checks screen with real-time monitoring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from freya.config import Settings

from ..checks import BaseSystemCheck
from ..checks.audio_check import MicrophoneCheck, SpeakerCheck
from ..checks.memory_check import MemoryCheck
from ..checks.ollama_check import OllamaCheck
from ..checks.python_check import PythonCheck
from ..checks.tts_check import TTSCheck
from ..checks.whisper_check import WhisperCheck


class SystemChecksScreen(Screen):
    """Screen for running system checks."""

    BINDINGS = [
        ("r", "run_checks", "Run Checks"),
        ("c", "continue_app", "Continue"),
        ("q", "quit_screen", "Back"),
    ]

    def __init__(self, config: Settings):
        super().__init__()
        self.config = config
        self.checks: list[BaseSystemCheck] = []
        self._create_checks()

    def _create_checks(self) -> None:
        """Create all system checks based on config."""
        self.checks = [
            PythonCheck(min_version=(3, 11)),
            OllamaCheck(
                host=self.config.ollama.host,
                model=self.config.ollama.model,
            ),
            WhisperCheck(
                model=self.config.stt.model_id,
                device=self.config.stt.device,
            ),
            MicrophoneCheck(),
            SpeakerCheck(),
            TTSCheck(engine=self.config.tts.engine),
            MemoryCheck(db_path=self.config.memory.long_term.db_path),
        ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Vertical():
            yield Static("System Checks", classes="section-header")

            # Status summary
            yield Static("", id="status-summary")

            # Checks table
            table = DataTable(id="checks-table")
            table.add_columns("Status", "Component", "Message", "Details")
            table.cursor_type = "row"
            yield table

            # Action buttons
            with Horizontal(id="button-row"):
                yield Button("Run All Checks", id="run-checks", variant="primary")
                yield Button("Continue", id="continue", variant="success")
                yield Button("Exit", id="exit", variant="default")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize screen when mounted."""
        # Populate table with checks
        table = self.query_one("#checks-table", DataTable)

        for check in self.checks:
            table.add_row(
                check.status.icon,
                check.name,
                check.description,
                "",
                key=check.name,
            )

        # Auto-run checks on mount
        await self.action_run_checks()

    async def action_run_checks(self) -> None:
        """Run all system checks."""
        table = self.query_one("#checks-table", DataTable)
        summary = self.query_one("#status-summary", Static)

        summary.update("Running checks...")

        passed = 0
        failed = 0
        warnings = 0

        for check in self.checks:
            # Update status to running
            table.update_cell(
                check.name,
                "Status",
                check.status.icon,
                update_width=True,
            )

            # Run check
            result = await check.execute()

            # Update table
            table.update_cell(check.name, "Status", result.status.icon)
            table.update_cell(check.name, "Message", result.message)
            table.update_cell(
                check.name,
                "Details",
                result.details or (result.fix_suggestion or ""),
            )

            # Count results
            if result.status.value == "passed":
                passed += 1
            elif result.status.value == "failed":
                failed += 1
            elif result.status.value == "warning":
                warnings += 1

        # Update summary
        total = len(self.checks)
        if failed > 0:
            summary_text = f"[bold red]✗ {failed} checks failed[/] | {passed}/{total} passed | {warnings} warnings"
        elif warnings > 0:
            summary_text = f"[bold yellow]⚠ {warnings} warnings[/] | {passed}/{total} passed"
        else:
            summary_text = f"[bold green]✓ All checks passed[/] ({passed}/{total})"

        summary.update(summary_text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "run-checks":
            await self.action_run_checks()
        elif event.button.id == "continue":
            await self.action_continue_app()
        elif event.button.id == "exit":
            await self.action_quit_screen()

    async def action_continue_app(self) -> None:
        """Continue to main app."""
        # Check if any required checks failed
        failed_required = [
            check
            for check in self.checks
            if check.required and check.status.value == "failed"
        ]

        if failed_required:
            self.notify(
                "Cannot continue: Some required checks failed",
                severity="error",
                timeout=5,
            )
            return

        self.app.pop_screen()

    async def action_quit_screen(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
