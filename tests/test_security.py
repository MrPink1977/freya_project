"""Comprehensive security tests for Freya vulnerability fixes."""

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path to import freya modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from freya.tools.calculator import CalculatorTool
from freya.tools.file_tools import ListFilesTool, ReadFileTool, WriteFileTool
from freya.tools.system_tools import ExecuteCommandTool


class TestCalculatorSecurity:
    """Test AST-based calculator blocks code injection attacks."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return CalculatorTool()

    def test_blocks_import_attack(self, calculator):
        """Verify __import__('os').system('ls') is blocked."""
        result = calculator.execute("__import__('os').system('ls')")
        assert not result.success
        assert "allowed" in result.error.lower()

    def test_blocks_eval_attack(self, calculator):
        """Verify eval('malicious code') is blocked."""
        result = calculator.execute("eval('1+1')")
        assert not result.success
        assert "unsafe" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_exec_attack(self, calculator):
        """Verify exec('malicious code') is blocked."""
        result = calculator.execute("exec('import os')")
        assert not result.success
        assert "unsafe" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_open_attack(self, calculator):
        """Verify open('/etc/passwd') is blocked."""
        result = calculator.execute("open('/etc/passwd').read()")
        assert not result.success
        assert "allowed" in result.error.lower()

    def test_blocks_compile_attack(self, calculator):
        """Verify compile() is blocked."""
        result = calculator.execute("compile('1+1', '<string>', 'eval')")
        assert not result.success
        assert "unsafe" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_globals_attack(self, calculator):
        """Verify globals() access is blocked."""
        result = calculator.execute("globals()")
        assert not result.success
        assert "unsafe" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_locals_attack(self, calculator):
        """Verify locals() access is blocked."""
        result = calculator.execute("locals()")
        assert not result.success
        assert "unsafe" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_vars_attack(self, calculator):
        """Verify vars() access is blocked."""
        result = calculator.execute("vars()")
        assert not result.success
        assert "unsafe" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_dir_attack(self, calculator):
        """Verify dir() access is blocked."""
        result = calculator.execute("dir()")
        assert not result.success
        assert "unsafe" in result.error.lower() or "not allowed" in result.error.lower()

    def test_allows_safe_math(self, calculator):
        """Verify legitimate mathematical expressions work."""
        # Basic arithmetic
        result = calculator.execute("2 + 2")
        assert result.success
        assert "4" in result.output

        # Complex expression
        result = calculator.execute("(3 + 5) * 2 / 4")
        assert result.success
        assert result.metadata["result"] == 4.0

        # Power
        result = calculator.execute("2 ** 8")
        assert result.success
        assert "256" in result.output

    def test_allows_safe_functions(self, calculator):
        """Verify whitelisted math functions work."""
        # sqrt
        result = calculator.execute("sqrt(16)")
        assert result.success
        assert result.metadata["result"] == 4.0

        # sin/cos (verify they execute, don't check exact value)
        result = calculator.execute("sin(0)")
        assert result.success

        # abs
        result = calculator.execute("abs(-5)")
        assert result.success
        assert result.metadata["result"] == 5.0

    def test_allows_constants(self, calculator):
        """Verify mathematical constants work."""
        # pi
        result = calculator.execute("pi")
        assert result.success
        assert 3.14 < result.metadata["result"] < 3.15

        # e
        result = calculator.execute("e")
        assert result.success
        assert 2.71 < result.metadata["result"] < 2.72


class TestPathTraversalSecurity:
    """Test file tools block path traversal attacks."""

    @pytest.fixture
    def list_tool(self):
        """Create list files tool."""
        return ListFilesTool()

    @pytest.fixture
    def read_tool(self):
        """Create read file tool."""
        return ReadFileTool()

    @pytest.fixture
    def write_tool(self):
        """Create write file tool."""
        return WriteFileTool()

    def test_blocks_unix_etc_passwd(self, read_tool):
        """Verify reading /etc/passwd is blocked."""
        result = read_tool.execute("/etc/passwd")
        assert not result.success
        assert "access denied" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_relative_traversal(self, read_tool):
        """Verify ../../../../../../etc/passwd is blocked."""
        result = read_tool.execute("../../../../../../etc/passwd")
        assert not result.success
        assert "access denied" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_windows_system32(self, read_tool):
        """Verify reading C:\\Windows\\System32\\config\\SAM is blocked."""
        if os.name != "nt":
            pytest.skip("Windows-specific test")
        result = read_tool.execute("C:\\Windows\\System32\\config\\SAM")
        assert not result.success
        assert "access denied" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_absolute_paths_outside_whitelist(self, read_tool):
        """Verify absolute paths outside whitelist are blocked."""
        result = read_tool.execute("/tmp/malicious.txt")
        assert not result.success
        assert "access denied" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_traversal_in_list(self, list_tool):
        """Verify list tool also blocks traversal."""
        result = list_tool.execute("../../../../../../etc")
        assert not result.success
        assert "access denied" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_traversal_in_write(self, write_tool):
        """Verify write tool blocks traversal."""
        result = write_tool.execute("/etc/malicious.txt", "content")
        assert not result.success
        assert "access denied" in result.error.lower() or "not allowed" in result.error.lower()

    def test_allows_documents_folder(self, tmp_path, read_tool):
        """Verify reading from Documents folder works (if it exists)."""
        docs = Path.home() / "Documents"
        if not docs.exists():
            pytest.skip("Documents folder doesn't exist")

        # Create test file
        test_file = docs / "freya_security_test.txt"
        try:
            test_file.write_text("test content")
            result = read_tool.execute(str(test_file))
            # Should either succeed or fail gracefully (not a security error)
            if not result.success:
                assert "access denied" not in result.error.lower()
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    def test_allows_data_folder(self, read_tool):
        """Verify reading from data/ folder works."""
        data_dir = Path("data")
        if not data_dir.exists():
            data_dir.mkdir(parents=True)

        test_file = data_dir / "security_test.txt"
        try:
            test_file.write_text("test content")
            result = read_tool.execute(str(test_file))
            assert result.success or "access denied" not in result.error.lower()
        finally:
            if test_file.exists():
                test_file.unlink()


class TestCommandInjectionSecurity:
    """Test system tools block command injection attacks."""

    @pytest.fixture
    def run_tool(self):
        """Create run command tool."""
        return ExecuteCommandTool()

    def test_blocks_semicolon_chaining(self, run_tool):
        """Verify ls; rm -rf / is blocked."""
        result = run_tool.execute("ls; rm -rf /")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_pipe_chaining(self, run_tool):
        """Verify ls | grep secret is blocked."""
        result = run_tool.execute("ls | grep secret")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_and_chaining(self, run_tool):
        """Verify ls && rm file is blocked."""
        result = run_tool.execute("ls && rm file")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_or_chaining(self, run_tool):
        """Verify ls || rm file is blocked."""
        result = run_tool.execute("ls || rm file")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_backtick_substitution(self, run_tool):
        """Verify command `whoami` substitution is blocked."""
        result = run_tool.execute("echo `whoami`")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_dollar_substitution(self, run_tool):
        """Verify command $(whoami) substitution is blocked."""
        result = run_tool.execute("echo $(whoami)")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_redirect_output(self, run_tool):
        """Verify output redirection > is blocked."""
        result = run_tool.execute("ls > /tmp/output.txt")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_redirect_input(self, run_tool):
        """Verify input redirection < is blocked."""
        result = run_tool.execute("cat < /etc/passwd")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_background_process(self, run_tool):
        """Verify background process & is blocked."""
        result = run_tool.execute("sleep 100 &")
        assert not result.success
        assert "security" in result.error.lower() or "not allowed" in result.error.lower()

    def test_blocks_unauthorized_command(self, run_tool):
        """Verify commands not in whitelist are blocked."""
        result = run_tool.execute("rm")
        assert not result.success
        assert "not allowed" in result.error.lower() or "not in whitelist" in result.error.lower()

    def test_allows_whitelisted_commands(self, run_tool):
        """Verify whitelisted commands work."""
        # whoami should be in whitelist
        result = run_tool.execute("whoami")
        # Should succeed or fail with non-security error
        if not result.success:
            assert "security" not in result.error.lower()
            assert "not allowed" not in result.error.lower()


class TestFrozenDataclassSecurity:
    """Test frozen dataclass configuration cannot be mutated."""

    def test_frozen_dataclass_immutability(self):
        """Verify config dataclasses are frozen and cannot be mutated directly."""
        from freya.core.config import load_settings

        config = load_settings()

        # Attempt to modify frozen dataclass should raise AttributeError
        with pytest.raises(AttributeError):
            config.app.interaction_mode = "malicious_mode"

        with pytest.raises(AttributeError):
            config.tts.engine = "malicious_engine"

        with pytest.raises(AttributeError):
            config.ollama.model = "malicious_model"


class TestEnvironmentVariableSecurity:
    """Test environment variable override works securely."""

    def test_env_override_works(self, monkeypatch):
        """Verify ELEVENLABS_API_KEY can be overridden via environment."""
        from freya.core.config import load_settings

        # Set test API key
        test_key = "sk_test_security_key_12345"
        monkeypatch.setenv("ELEVENLABS_API_KEY", test_key)

        # Load config
        config = load_settings()

        # Verify override worked - tts.elevenlabs.api_key
        assert config.tts.elevenlabs.api_key == test_key

    def test_no_hardcoded_secrets(self):
        """Verify no hardcoded API keys in default config."""
        from pathlib import Path

        import yaml

        config_path = Path(__file__).parent.parent / "config" / "default.yaml"
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        # Check ElevenLabs API key is empty
        api_key = config_data.get("tts_elevenlabs", {}).get("api_key", "")
        assert api_key == "" or api_key is None, "Hardcoded API key found in config!"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
