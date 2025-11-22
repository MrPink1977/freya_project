"""Main Textual application for Freya TUI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static
from textual.containers import Vertical

if TYPE_CHECKING:
    from freya.config import Settings

from .screens.system_checks import SystemChecksScreen


class MainScreen(Static):
    """Main dashboard screen."""

    def compose(self) -> ComposeResult:
        """Compose main screen."""
        with Vertical():
            yield Static(
                """
╔══════════════════════════════════════════════════════════════╗
║                    FREYA AI ASSISTANT                         ║
║                  Terminal User Interface                      ║
╚══════════════════════════════════════════════════════════════╝

Welcome to Freya TUI!

Available Screens:
  • F1 - System Checks    (Verify all components)
  • F2 - Configuration    (Edit settings)
  • F3 - Chat Interface   (Talk with Freya)
  • F4 - Log Viewer       (Monitor system logs)
  • F5 - Test Runner      (Run integration tests)

Press F1 to start with System Checks
Press F10 or Ctrl+C to quit
""",
                id="welcome-text",
            )


class FreyaApp(App):
    """Freya TUI Application."""

    CSS_PATH = Path(__file__).parent / "themes" / "dark.tcss"

    TITLE = "Freya AI Assistant"
    SUB_TITLE = "Agent-Based Architecture | Multi-Channel Audio | 9 Tools"

    BINDINGS = [
        Binding("f1", "push_screen('checks')", "System Checks", priority=True),
        Binding("f2", "push_screen('config')", "Configuration", show=False),
        Binding("f3", "push_screen('chat')", "Chat", show=False),
        Binding("f4", "push_screen('logs')", "Logs", show=False),
        Binding("f5", "push_screen('tests')", "Tests", show=False),
        Binding("f10", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
    ]

    SCREENS = {
        "checks": SystemChecksScreen,
    }

    def __init__(self, config: Settings):
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)
        yield MainScreen()
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE

    def action_push_screen(self, screen_name: str) -> None:
        """Push a named screen."""
        if screen_name == "checks":
            self.push_screen(SystemChecksScreen(self.config))
        elif screen_name == "config":
            self.notify("Configuration screen coming soon!", timeout=3)
        elif screen_name == "chat":
            self.notify("Chat screen coming soon!", timeout=3)
        elif screen_name == "logs":
            self.notify("Log viewer coming soon!", timeout=3)
        elif screen_name == "tests":
            self.notify("Test runner coming soon!", timeout=3)
