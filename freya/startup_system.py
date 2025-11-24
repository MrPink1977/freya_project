"""Comprehensive startup system with checks, menu, and test logging."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    Fore = Style = None  # type: ignore

from .config import Settings
from .logger import get_logger
from .system_check import SystemCheck

logger = get_logger("startup_system")


class StartupSystem:
    """Manages comprehensive startup sequence with checks, menu, and logging."""
    
    def __init__(self, config: Settings):
        self.config = config
        self.checker = SystemCheck()
        self.test_log: list[str] = []
        self.start_time = datetime.now()
        
    def log_test(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.test_log.append(log_entry)
        logger.info(message)
        
    def print_colored(self, message: str, color=None):
        """Print colored message."""
        if Fore and color:
            print(f"{color}{message}{Style.RESET_ALL}")
        else:
            print(message)
            
    def print_box(self, message: str, color=None, width: int = 70):
        """Print message in a colored box."""
        if Fore and color:
            border = "═" * (width - 4)
            print(f"{color}╔═{border}═╗")
            print(f"{color}║ {message.ljust(width - 4)} ║")
            print(f"{color}╚═{border}═╝{Style.RESET_ALL}")
        else:
            print(f"\n{'=' * width}")
            print(f"  {message}")
            print(f"{'=' * width}\n")
    
    def run_system_checks(self) -> Dict[str, tuple[bool, str]]:
        """Run all system checks and display results with green lights."""
        self.print_box("FREYA SYSTEM CHECKS", Fore.CYAN, 70)
        self.log_test("Starting system checks")
        
        checks = {}
        
        # Check 1: Ollama
        self.print_colored("\n[1/7] Checking Ollama connection...", Fore.YELLOW)
        checks['ollama'] = self.checker._check_ollama(
            self.config.ollama.host,
            self.config.ollama.model
        )
        self._print_check_result("Ollama", checks['ollama'])
        
        # Check 2: Whisper STT
        self.print_colored("\n[2/7] Checking Whisper STT...", Fore.YELLOW)
        checks['whisper'] = self.checker._check_whisper(self.config.stt.device)
        self._print_check_result("Whisper STT", checks['whisper'])
        
        # Check 3: Microphone
        self.print_colored("\n[3/7] Checking microphone access...", Fore.YELLOW)
        checks['microphone'] = self.checker._check_microphone()
        self._print_check_result("Microphone", checks['microphone'])
        
        # Check 4: TTS Engine
        self.print_colored("\n[4/7] Checking TTS engine...", Fore.YELLOW)
        checks['tts'] = self.checker._check_tts(self.config.tts.voice_path)
        self._print_check_result("TTS Engine", checks['tts'])
        
        # Check 5: Wake Word Detector
        self.print_colored("\n[5/7] Checking wake word detector...", Fore.YELLOW)
        checks['wake'] = self.checker._check_wake_detector(self.config.wake_detector)
        self._print_check_result("Wake Detector", checks['wake'])
        
        # Check 6: Memory Store
        self.print_colored("\n[6/7] Checking memory store...", Fore.YELLOW)
        checks['memory'] = self.checker._check_memory(self.config.memory.long_term)
        self._print_check_result("Memory Store", checks['memory'])
        
        # Check 7: Color Display Test
        self.print_colored("\n[7/7] Testing color display...", Fore.YELLOW)
        checks['colors'] = self._test_color_display()
        self._print_check_result("Color Display", checks['colors'])
        
        # Summary
        passed = sum(1 for ok, _ in checks.values() if ok)
        total = len(checks)
        self.log_test(f"System checks complete: {passed}/{total} passed")
        
        if passed == total:
            self.print_box(f"✓ ALL SYSTEMS GREEN ({passed}/{total})", Fore.GREEN, 70)
        else:
            self.print_box(f"⚠ WARNINGS ({passed}/{total} passed)", Fore.YELLOW, 70)
            
        return checks
    
    def _print_check_result(self, name: str, result: tuple[bool, str]):
        """Print check result with green light or red X."""
        ok, msg = result
        if ok:
            self.print_colored(f"  ✓ {name}: {msg}", Fore.GREEN)
            self.log_test(f"{name} check PASSED: {msg}")
        else:
            self.print_colored(f"  ✗ {name}: {msg}", Fore.RED)
            self.log_test(f"{name} check FAILED: {msg}", "ERROR")
    
    def _test_color_display(self) -> tuple[bool, str]:
        """Test color display capabilities."""
        try:
            if not Fore:
                return False, "colorama not available"
            
            # Test cyan (user)
            print(f"    {Fore.CYAN}User text test (cyan){Style.RESET_ALL}")
            # Test magenta (Freya)
            print(f"    {Fore.MAGENTA}Freya text test (magenta){Style.RESET_ALL}")
            # Test green (success)
            print(f"    {Fore.GREEN}Success text test (green){Style.RESET_ALL}")
            # Test red (error)
            print(f"    {Fore.RED}Error text test (red){Style.RESET_ALL}")
            
            return True, "All colors displayed correctly"
        except Exception as e:
            return False, f"Color test failed: {e}"
    
    def show_configuration(self):
        """Display current configuration."""
        self.print_box("CURRENT CONFIGURATION", Fore.CYAN, 70)
        
        print(f"{Fore.YELLOW}Dialog Model:{Style.RESET_ALL}")
        print(f"  Host: {self.config.ollama.host}")
        print(f"  Model: {self.config.ollama.model}")
        print(f"  Temperature: {self.config.ollama.options.get('temperature', 0.7)}")
        
        print(f"\n{Fore.YELLOW}Speech Recognition:{Style.RESET_ALL}")
        print(f"  Model: {self.config.stt.model_id}")
        print(f"  Device: {self.config.stt.device}")
        print(f"  Language: {self.config.stt.language}")
        
        print(f"\n{Fore.YELLOW}Text-to-Speech:{Style.RESET_ALL}")
        print(f"  Engine: {self.config.tts.engine}")
        if self.config.tts.engine == "piper":
            print(f"  Model: {self.config.tts.piper_model}")
        
        print(f"\n{Fore.YELLOW}Wake Word:{Style.RESET_ALL}")
        print(f"  Model: {self.config.wake_detector.model}")
        print(f"  Threshold: {self.config.wake_detector.threshold}")
        
        print()
    
    def show_controls(self):
        """Display available controls."""
        self.print_box("AVAILABLE CONTROLS", Fore.CYAN, 70)
        
        print(f"{Fore.GREEN}Emergency Controls:{Style.RESET_ALL}")
        print(f"  Ctrl+M           - Mute/Unmute Freya")
        print(f"  Escape (hold)    - Emergency stop (releases all locks)")
        
        print(f"\n{Fore.GREEN}Natural Exit Phrases:{Style.RESET_ALL}")
        print(f"  'Freya be quiet', 'zip it', 'shut up', 'stop talking'")
        print(f"  'enough', 'that's enough', 'silence please'")
        
        print(f"\n{Fore.GREEN}Text Mode:{Style.RESET_ALL}")
        print(f"  Type 'exit', 'quit', 'bye', 'goodbye' to end session")
        
        print()
    
    def show_startup_menu(self) -> Optional[str]:
        """Show interactive startup menu and return user choice."""
        self.print_box("FREYA STARTUP MENU", Fore.MAGENTA, 70)
        
        print(f"{Fore.CYAN}Choose an option:{Style.RESET_ALL}\n")
        print(f"  {Fore.GREEN}1{Style.RESET_ALL} - Start Freya (Voice Mode)")
        print(f"  {Fore.GREEN}2{Style.RESET_ALL} - Start Freya (Text Mode)")
        print(f"  {Fore.GREEN}3{Style.RESET_ALL} - View Configuration")
        print(f"  {Fore.GREEN}4{Style.RESET_ALL} - View Controls & Hotkeys")
        print(f"  {Fore.GREEN}5{Style.RESET_ALL} - Re-run System Checks")
        print(f"  {Fore.GREEN}6{Style.RESET_ALL} - Change Model")
        print(f"  {Fore.GREEN}7{Style.RESET_ALL} - Toggle Facial Recognition")
        print(f"  {Fore.GREEN}8{Style.RESET_ALL} - View Test Log")
        print(f"  {Fore.GREEN}Q{Style.RESET_ALL} - Quit")
        
        print()
        choice = input(f"{Fore.YELLOW}Enter choice: {Style.RESET_ALL}").strip().lower()
        self.log_test(f"Menu choice: {choice}")
        return choice
    
    def handle_menu_choice(self, choice: str) -> tuple[bool, Optional[str]]:
        """
        Handle menu choice.
        Returns: (continue_menu, mode_to_start)
            continue_menu: True to show menu again, False to exit
            mode_to_start: "voice", "text", or None
        """
        if choice == "1":
            self.print_colored("\n→ Starting Freya in VOICE mode...\n", Fore.GREEN)
            self.log_test("User selected: Start Voice Mode")
            return False, "voice"
        
        elif choice == "2":
            self.print_colored("\n→ Starting Freya in TEXT mode...\n", Fore.GREEN)
            self.log_test("User selected: Start Text Mode")
            return False, "text"
        
        elif choice == "3":
            self.show_configuration()
            input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
            return True, None
        
        elif choice == "4":
            self.show_controls()
            input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
            return True, None
        
        elif choice == "5":
            self.run_system_checks()
            input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
            return True, None
        
        elif choice == "6":
            self._change_model_menu()
            return True, None
        
        elif choice == "7":
            self._toggle_facial_recognition()
            return True, None
        
        elif choice == "8":
            self._show_test_log()
            input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
            return True, None
        
        elif choice == "q":
            self.print_colored("\nGoodbye!\n", Fore.CYAN)
            self.log_test("User quit from menu")
            return False, None
        
        else:
            self.print_colored(f"\n⚠ Invalid choice: {choice}\n", Fore.RED)
            return True, None
    
    def _change_model_menu(self):
        """Show model selection submenu."""
        self.print_box("CHANGE DIALOG MODEL", Fore.CYAN, 70)
        
        print(f"{Fore.YELLOW}Current model:{Style.RESET_ALL} {self.config.ollama.model}\n")
        print("Common models:")
        print("  1 - llama3.2:3b")
        print("  2 - llama3.2:1b")
        print("  3 - mistral")
        print("  4 - Custom (type model name)")
        print()
        
        choice = input(f"{Fore.YELLOW}Select model: {Style.RESET_ALL}").strip()
        
        if choice == "1":
            self.config.ollama.model = "llama3.2:3b"
        elif choice == "2":
            self.config.ollama.model = "llama3.2:1b"
        elif choice == "3":
            self.config.ollama.model = "mistral"
        elif choice == "4":
            model = input(f"{Fore.YELLOW}Enter model name: {Style.RESET_ALL}").strip()
            if model:
                self.config.ollama.model = model
        
        self.print_colored(f"\n✓ Model set to: {self.config.ollama.model}\n", Fore.GREEN)
        self.log_test(f"Model changed to: {self.config.ollama.model}")
    
    def _toggle_facial_recognition(self):
        """Toggle facial recognition on/off."""
        current = self.config.facial_recognition.enabled
        self.config.facial_recognition.enabled = not current
        
        status = "ENABLED" if self.config.facial_recognition.enabled else "DISABLED"
        color = Fore.GREEN if self.config.facial_recognition.enabled else Fore.RED
        self.print_colored(f"\n✓ Facial recognition {status}\n", color)
        self.log_test(f"Facial recognition toggled: {status}")
        input(f"{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
    
    def _show_test_log(self):
        """Display test log entries."""
        self.print_box("TEST LOG", Fore.CYAN, 70)
        
        if not self.test_log:
            print(f"{Fore.YELLOW}No log entries yet.{Style.RESET_ALL}")
        else:
            for entry in self.test_log:
                if "[ERROR]" in entry:
                    print(f"{Fore.RED}{entry}{Style.RESET_ALL}")
                elif "[WARN]" in entry:
                    print(f"{Fore.YELLOW}{entry}{Style.RESET_ALL}")
                else:
                    print(entry)
        print()
    
    def save_test_log(self, output_path: Optional[Path] = None):
        """Save test log to file."""
        if output_path is None:
            output_path = Path("freya_startup_test.log")
        
        try:
            with open(output_path, "w") as f:
                f.write(f"Freya Startup Test Log\n")
                f.write(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                for entry in self.test_log:
                    f.write(entry + "\n")
            
            self.print_colored(f"✓ Test log saved to: {output_path}", Fore.GREEN)
            logger.info(f"Test log saved to: {output_path}")
        except Exception as e:
            self.print_colored(f"✗ Failed to save test log: {e}", Fore.RED)
            logger.error(f"Failed to save test log: {e}")


def run_interactive_startup(config: Settings) -> Optional[str]:
    """
    Run complete interactive startup sequence.
    Returns the mode to start ("voice", "text") or None to quit.
    """
    startup = StartupSystem(config)
    
    # Welcome banner
    startup.print_box("WELCOME TO FREYA AI ASSISTANT", Fore.MAGENTA, 70)
    startup.log_test("Startup sequence initiated")
    
    # Run system checks first
    checks = startup.run_system_checks()
    
    # Check if any critical systems failed
    critical_failed = []
    if not checks.get('ollama', (False, ""))[0]:
        critical_failed.append("Ollama")
    if not checks.get('microphone', (False, ""))[0]:
        critical_failed.append("Microphone")
    
    if critical_failed:
        startup.print_colored(
            f"\n⚠ WARNING: Critical systems failed: {', '.join(critical_failed)}", 
            Fore.RED
        )
        choice = input(f"\n{Fore.YELLOW}Continue anyway? (y/n): {Style.RESET_ALL}").strip().lower()
        if choice != "y":
            startup.log_test("User aborted due to failed critical checks")
            startup.save_test_log()
            return None
    
    # Interactive menu loop
    while True:
        print()  # Spacing
        choice = startup.show_startup_menu()
        continue_menu, mode = startup.handle_menu_choice(choice)
        
        if not continue_menu:
            if mode:
                startup.log_test(f"Starting Freya in {mode} mode")
            startup.save_test_log()
            return mode
