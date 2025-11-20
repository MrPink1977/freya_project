"""Comprehensive tests for file operation tools."""

from __future__ import annotations

import pytest
from pathlib import Path
from freya.tools.file_tools import (
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
    validate_path,
    ALLOWED_DIRECTORIES,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def list_files_tool():
    """Provide ListFilesTool instance."""
    return ListFilesTool()


@pytest.fixture
def read_file_tool():
    """Provide ReadFileTool instance."""
    return ReadFileTool()


@pytest.fixture
def write_file_tool():
    """Provide WriteFileTool instance."""
    return WriteFileTool()


@pytest.fixture
def safe_test_dir(tmp_path):
    """Create a temporary test directory within allowed paths."""
    # Use project data directory which is in ALLOWED_DIRECTORIES
    test_dir = Path.cwd() / "data" / "test_files"
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    
    # Cleanup after test
    import shutil
    if test_dir.exists():
        shutil.rmtree(test_dir)


# ============================================================================
# PATH VALIDATION TESTS (Security Critical)
# ============================================================================


class TestPathValidation:
    """Test path traversal protection."""

    def test_blocks_parent_directory_traversal(self):
        """Block path traversal attempts with .."""
        dangerous_paths = [
            "../../../etc/passwd",
            "../../Windows/System32/config/sam",
            str(Path.home() / "Documents" / ".." / ".." / ".." / "etc" / "passwd"),
        ]
        
        for path in dangerous_paths:
            resolved, error = validate_path(path)
            assert resolved is None, f"Should block path traversal: {path}"
            assert error is not None, f"Should return error for: {path}"
            assert "outside allowed directories" in error.lower()

    def test_blocks_absolute_paths_outside_allowed(self):
        """Block absolute paths outside allowed directories."""
        dangerous_paths = [
            "/etc/passwd",
            "C:/Windows/System32/config/sam",
            "/var/log/syslog",
            str(Path("/root/.ssh/id_rsa")),
        ]
        
        for path in dangerous_paths:
            resolved, error = validate_path(path)
            assert resolved is None, f"Should block absolute path: {path}"
            assert error is not None, f"Should return error for: {path}"

    def test_blocks_symlink_escape(self, safe_test_dir):
        """Block symlinks pointing outside allowed directories."""
        # Create symlink to /etc (outside allowed dirs)
        symlink = safe_test_dir / "escape_link"
        target = Path("/etc") if Path("/etc").exists() else Path("C:/Windows")
        
        try:
            symlink.symlink_to(target)
            resolved, error = validate_path(str(symlink))
            
            # Should either block (resolved=None) or resolve to target
            # If it resolves, check target is blocked
            if resolved:
                # Validate resolved target is not in /etc or C:/Windows
                assert not str(resolved).startswith("/etc")
                assert not str(resolved).startswith("C:/Windows")
        except OSError:
            # Symlink creation may fail on Windows without admin rights - skip test
            pytest.skip("Cannot create symlinks (need admin rights on Windows)")

    def test_allows_paths_in_allowed_directories(self, safe_test_dir):
        """Allow valid paths within allowed directories."""
        # Test with safe_test_dir which is in ALLOWED_DIRECTORIES
        test_file = safe_test_dir / "valid_file.txt"
        test_file.write_text("test")
        
        resolved, error = validate_path(str(test_file))
        assert resolved is not None, f"Should allow path in safe directory: {test_file}"
        assert error is None
        assert resolved == test_file.resolve()

    def test_allows_relative_paths_in_allowed_dirs(self, safe_test_dir):
        """Allow relative paths that resolve to allowed directories."""
        # Create a file in safe_test_dir
        test_file = safe_test_dir / "test.txt"
        test_file.write_text("test")
        
        # Test relative path
        resolved, error = validate_path("data/test_files/test.txt")
        assert error is None, f"Should allow relative path in allowed dir"
        assert resolved is not None

    def test_handles_invalid_path_syntax(self):
        """Handle invalid path syntax gracefully."""
        invalid_paths = [
            "\x00null_byte_injection",
            "invalid\npath\nwith\nnewlines",
        ]
        
        for path in invalid_paths:
            resolved, error = validate_path(path)
            # Should either block or handle gracefully
            assert error is not None or resolved is None


# ============================================================================
# LIST FILES TOOL TESTS
# ============================================================================


class TestListFilesTool:
    """Test file listing functionality."""

    def test_lists_files_in_directory(self, list_files_tool, safe_test_dir):
        """List files in a safe directory."""
        # Create test files
        (safe_test_dir / "file1.txt").write_text("content1")
        (safe_test_dir / "file2.txt").write_text("content2")
        (safe_test_dir / "subdir").mkdir()
        
        result = list_files_tool.execute(path=str(safe_test_dir))
        
        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
        assert "subdir" in result.output

    def test_pattern_matching(self, list_files_tool, safe_test_dir):
        """Filter files by pattern."""
        (safe_test_dir / "test.txt").write_text("text")
        (safe_test_dir / "test.py").write_text("code")
        (safe_test_dir / "data.json").write_text("data")
        
        result = list_files_tool.execute(path=str(safe_test_dir), pattern="*.txt")
        
        assert result.success is True
        assert "test.txt" in result.output
        assert "test.py" not in result.output
        assert "data.json" not in result.output

    def test_recursive_listing(self, list_files_tool, safe_test_dir):
        """List files recursively."""
        subdir = safe_test_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")
        (safe_test_dir / "root.txt").write_text("root")
        
        result = list_files_tool.execute(path=str(safe_test_dir), recursive=True)
        
        assert result.success is True
        assert "root.txt" in result.output
        assert "nested.txt" in result.output or "subdir" in result.output

    def test_blocks_listing_outside_allowed_dirs(self, list_files_tool):
        """Block listing directories outside allowed paths."""
        dangerous_paths = ["/etc", "C:/Windows/System32", "/root"]
        
        for path in dangerous_paths:
            result = list_files_tool.execute(path=path)
            assert result.success is False
            assert result.error is not None
            assert "outside allowed directories" in result.error.lower() or "access denied" in result.error.lower()

    def test_handles_nonexistent_directory(self, list_files_tool, safe_test_dir):
        """Handle nonexistent directory gracefully."""
        nonexistent = safe_test_dir / "does_not_exist"
        result = list_files_tool.execute(path=str(nonexistent))
        
        assert result.success is False
        assert "does not exist" in result.error.lower()

    def test_metadata_includes_counts(self, list_files_tool, safe_test_dir):
        """Metadata includes file and directory counts."""
        (safe_test_dir / "file1.txt").write_text("1")
        (safe_test_dir / "file2.txt").write_text("2")
        (safe_test_dir / "subdir").mkdir()
        
        result = list_files_tool.execute(path=str(safe_test_dir))
        
        assert result.success is True
        assert "file_count" in result.metadata
        assert "dir_count" in result.metadata
        assert result.metadata["file_count"] >= 2
        assert result.metadata["dir_count"] >= 1


# ============================================================================
# READ FILE TOOL TESTS
# ============================================================================


class TestReadFileTool:
    """Test file reading functionality."""

    def test_reads_text_file(self, read_file_tool, safe_test_dir):
        """Read a text file successfully."""
        test_file = safe_test_dir / "test.txt"
        content = "Hello, Freya!\nLine 2\nLine 3"
        test_file.write_text(content)
        
        result = read_file_tool.execute(path=str(test_file))
        
        assert result.success is True
        assert "Hello, Freya!" in result.output
        assert "Line 2" in result.output
        assert "Line 3" in result.output

    def test_respects_max_lines_limit(self, read_file_tool, safe_test_dir):
        """Respect max_lines parameter."""
        test_file = safe_test_dir / "long.txt"
        lines = [f"Line {i}" for i in range(200)]
        test_file.write_text("\n".join(lines))
        
        result = read_file_tool.execute(path=str(test_file), max_lines=50)
        
        assert result.success is True
        assert "truncated" in result.output.lower()
        assert result.metadata["lines_read"] <= 51  # 50 lines + truncation message

    def test_blocks_reading_outside_allowed_dirs(self, read_file_tool):
        """Block reading files outside allowed directories."""
        dangerous_files = [
            "/etc/passwd",
            "C:/Windows/System32/config/sam",
            "../../../etc/shadow",
        ]
        
        for path in dangerous_files:
            result = read_file_tool.execute(path=path)
            assert result.success is False
            assert result.error is not None

    def test_handles_nonexistent_file(self, read_file_tool, safe_test_dir):
        """Handle nonexistent file gracefully."""
        nonexistent = safe_test_dir / "missing.txt"
        result = read_file_tool.execute(path=str(nonexistent))
        
        assert result.success is False
        assert "does not exist" in result.error.lower()

    def test_handles_binary_file(self, read_file_tool, safe_test_dir):
        """Handle binary files gracefully."""
        binary_file = safe_test_dir / "binary.dat"
        binary_file.write_bytes(b"\x00\x01\x02\xff\xfe")
        
        result = read_file_tool.execute(path=str(binary_file))
        
        # Should either fail or handle gracefully
        if not result.success:
            assert "binary" in result.error.lower() or "decode" in result.error.lower()

    def test_metadata_includes_file_info(self, read_file_tool, safe_test_dir):
        """Metadata includes file information."""
        test_file = safe_test_dir / "info.txt"
        test_file.write_text("Test content")
        
        result = read_file_tool.execute(path=str(test_file))
        
        assert result.success is True
        assert "path" in result.metadata
        assert "size" in result.metadata
        assert "lines_read" in result.metadata


# ============================================================================
# WRITE FILE TOOL TESTS
# ============================================================================


class TestWriteFileTool:
    """Test file writing functionality."""

    def test_writes_new_file(self, write_file_tool, safe_test_dir):
        """Write content to a new file."""
        test_file = safe_test_dir / "new.txt"
        content = "Hello from Freya!"
        
        result = write_file_tool.execute(path=str(test_file), content=content)
        
        assert result.success is True
        assert test_file.exists()
        assert test_file.read_text() == content
        assert "wrote" in result.output.lower()

    def test_overwrites_existing_file(self, write_file_tool, safe_test_dir):
        """Overwrite existing file by default."""
        test_file = safe_test_dir / "existing.txt"
        test_file.write_text("Old content")
        
        new_content = "New content"
        result = write_file_tool.execute(path=str(test_file), content=new_content)
        
        assert result.success is True
        assert test_file.read_text() == new_content

    def test_appends_to_file(self, write_file_tool, safe_test_dir):
        """Append to file when append=True."""
        test_file = safe_test_dir / "append.txt"
        test_file.write_text("First line\n")
        
        result = write_file_tool.execute(
            path=str(test_file), 
            content="Second line\n", 
            append=True
        )
        
        assert result.success is True
        content = test_file.read_text()
        assert "First line" in content
        assert "Second line" in content
        assert "appended" in result.output.lower()

    def test_creates_parent_directories(self, write_file_tool, safe_test_dir):
        """Create parent directories if they don't exist."""
        nested_file = safe_test_dir / "sub1" / "sub2" / "file.txt"
        
        result = write_file_tool.execute(path=str(nested_file), content="nested")
        
        assert result.success is True
        assert nested_file.exists()
        assert nested_file.read_text() == "nested"

    def test_blocks_writing_outside_allowed_dirs(self, write_file_tool):
        """Block writing files outside allowed directories."""
        dangerous_files = [
            "/etc/dangerous.txt",
            "C:/Windows/System32/malware.exe",
            "../../../root/exploit.sh",
        ]
        
        for path in dangerous_files:
            result = write_file_tool.execute(path=path, content="malicious")
            assert result.success is False
            assert result.error is not None

    def test_metadata_includes_write_info(self, write_file_tool, safe_test_dir):
        """Metadata includes write information."""
        test_file = safe_test_dir / "meta.txt"
        content = "Test metadata"
        
        result = write_file_tool.execute(path=str(test_file), content=content)
        
        assert result.success is True
        assert "path" in result.metadata
        assert "bytes_written" in result.metadata
        assert "total_size" in result.metadata
        assert result.metadata["bytes_written"] == len(content)


# ============================================================================
# TOOL RESULT STRUCTURE TESTS
# ============================================================================


class TestFileToolsResult:
    """Test ToolResult structure compliance."""

    def test_list_files_result_structure(self, list_files_tool, safe_test_dir):
        """Validate ListFilesTool ToolResult structure."""
        (safe_test_dir / "test.txt").write_text("test")
        result = list_files_tool.execute(path=str(safe_test_dir))
        
        # Check success result
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "metadata")
        assert result.success is True
        assert isinstance(result.output, str)
        assert result.error is None or result.error == ""

    def test_read_file_result_structure(self, read_file_tool, safe_test_dir):
        """Validate ReadFileTool ToolResult structure."""
        test_file = safe_test_dir / "test.txt"
        test_file.write_text("content")
        result = read_file_tool.execute(path=str(test_file))
        
        assert result.success is True
        assert isinstance(result.output, str)
        assert result.metadata is not None

    def test_write_file_result_structure(self, write_file_tool, safe_test_dir):
        """Validate WriteFileTool ToolResult structure."""
        test_file = safe_test_dir / "test.txt"
        result = write_file_tool.execute(path=str(test_file), content="test")
        
        assert result.success is True
        assert isinstance(result.output, str)
        assert result.metadata is not None

    def test_error_result_structure(self, read_file_tool):
        """Validate error ToolResult structure."""
        result = read_file_tool.execute(path="/invalid/path/file.txt")
        
        assert result.success is False
        assert result.error is not None
        assert isinstance(result.error, str)
        assert len(result.error) > 0
