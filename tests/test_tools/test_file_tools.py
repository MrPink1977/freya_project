"""Comprehensive tests for file operation tools."""

from __future__ import annotations

import pytest
from pathlib import Path
from freya.tools.file_tools import (
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
    validate_path,
    validate_file_size,
    validate_file_type,
    ALLOWED_DIRECTORIES,
    ALLOWED_MIME_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_READ_SIZE,
    MAX_WRITE_SIZE,
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
        
        # Should reject due to unknown file type
        assert result.success is False
        assert (
            "binary" in result.error.lower()
            or "unknown" in result.error.lower()
            or "not allowed" in result.error.lower()
            or "decode" in result.error.lower()
        )

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


# ============================================================================
# FILE SIZE LIMIT TESTS
# ============================================================================


class TestFileSizeLimits:
    """Test file size validation and limits."""

    def test_validate_file_size_within_limit(self, safe_test_dir):
        """validate_file_size returns None for files within limit."""
        test_file = safe_test_dir / "small.txt"
        test_file.write_text("small content")
        
        error = validate_file_size(test_file, MAX_READ_SIZE, "read")
        assert error is None

    def test_validate_file_size_exceeds_limit(self, safe_test_dir):
        """validate_file_size returns error for oversized files."""
        test_file = safe_test_dir / "large.txt"
        # Create file larger than 1 MB limit
        large_content = "x" * (MAX_READ_SIZE + 1000)
        test_file.write_text(large_content)
        
        error = validate_file_size(test_file, MAX_READ_SIZE, "read")
        assert error is not None
        assert "too large" in error.lower()
        assert "MB" in error

    def test_read_file_rejects_oversized(self, read_file_tool, safe_test_dir):
        """ReadFileTool rejects files larger than MAX_READ_SIZE."""
        test_file = safe_test_dir / "huge.txt"
        # Create 1.5 MB file (exceeds 1 MB limit)
        large_content = "a" * (MAX_READ_SIZE + 500000)
        test_file.write_text(large_content)
        
        result = read_file_tool.execute(path=str(test_file))
        assert result.success is False
        assert "too large" in result.error.lower()
        assert "read" in result.error.lower()

    def test_read_file_accepts_max_size(self, read_file_tool, safe_test_dir):
        """ReadFileTool accepts files at exactly MAX_READ_SIZE."""
        test_file = safe_test_dir / "exactly_max.txt"
        # Create file exactly at limit
        content = "b" * MAX_READ_SIZE
        test_file.write_text(content)
        
        result = read_file_tool.execute(path=str(test_file))
        assert result.success is True

    def test_write_file_rejects_oversized_content(self, write_file_tool, safe_test_dir):
        """WriteFileTool rejects content larger than MAX_WRITE_SIZE."""
        test_file = safe_test_dir / "big_write.txt"
        # Try to write 11 MB (exceeds 10 MB limit)
        large_content = "c" * (MAX_WRITE_SIZE + 1000000)
        
        result = write_file_tool.execute(path=str(test_file), content=large_content)
        assert result.success is False
        assert "too large" in result.error.lower()
        assert "write" in result.error.lower()

    def test_write_file_accepts_max_size(self, write_file_tool, safe_test_dir):
        """WriteFileTool accepts content at exactly MAX_WRITE_SIZE."""
        test_file = safe_test_dir / "exactly_max_write.txt"
        # Write exactly at limit (10 MB)
        content = "d" * MAX_WRITE_SIZE
        
        result = write_file_tool.execute(path=str(test_file), content=content)
        assert result.success is True

    def test_append_within_limit(self, write_file_tool, safe_test_dir):
        """WriteFileTool allows append when final size within limit."""
        test_file = safe_test_dir / "append_ok.txt"
        # Create initial file with 1 MB
        initial_content = "e" * (1024 * 1024)
        test_file.write_text(initial_content)
        
        # Append 1 MB more (total 2 MB, well within 10 MB limit)
        append_content = "f" * (1024 * 1024)
        result = write_file_tool.execute(path=str(test_file), content=append_content, append=True)
        assert result.success is True

    def test_append_exceeds_limit(self, write_file_tool, safe_test_dir):
        """WriteFileTool rejects append when final size exceeds limit."""
        test_file = safe_test_dir / "append_too_big.txt"
        # Create file with 9 MB
        initial_content = "g" * (9 * 1024 * 1024)
        test_file.write_text(initial_content)
        
        # Try to append 2 MB more (total 11 MB, exceeds 10 MB limit)
        append_content = "h" * (2 * 1024 * 1024)
        result = write_file_tool.execute(path=str(test_file), content=append_content, append=True)
        assert result.success is False
        assert "append" in result.error.lower()
        assert "exceed" in result.error.lower()

    def test_size_in_metadata(self, read_file_tool, safe_test_dir):
        """File size included in read result metadata."""
        test_file = safe_test_dir / "with_size.txt"
        content = "test content with size"
        test_file.write_text(content)
        
        result = read_file_tool.execute(path=str(test_file))
        assert result.success is True
        assert "size" in result.metadata
        assert result.metadata["size"] == len(content)


# ============================================================================
# MIME TYPE VALIDATION TESTS
# ============================================================================


class TestMimeTypeValidation:
    """Test MIME type validation for file reading."""

    def test_validate_text_file_by_mime(self, safe_test_dir):
        """validate_file_type accepts text files by MIME type."""
        test_file = safe_test_dir / "test.txt"
        test_file.write_text("plain text content")
        
        mime_type, error = validate_file_type(test_file)
        assert error is None
        assert mime_type in ALLOWED_MIME_TYPES or "text" in mime_type.lower()

    def test_validate_json_file(self, safe_test_dir):
        """validate_file_type accepts JSON files."""
        test_file = safe_test_dir / "data.json"
        test_file.write_text('{"key": "value"}')
        
        mime_type, error = validate_file_type(test_file)
        assert error is None
        assert "json" in (mime_type or "").lower()

    def test_validate_python_file(self, safe_test_dir):
        """validate_file_type accepts Python files."""
        test_file = safe_test_dir / "script.py"
        test_file.write_text("print('hello')")
        
        mime_type, error = validate_file_type(test_file)
        assert error is None  # Should accept by extension

    def test_validate_yaml_file(self, safe_test_dir):
        """validate_file_type accepts YAML files."""
        test_file = safe_test_dir / "config.yaml"
        test_file.write_text("key: value")
        
        mime_type, error = validate_file_type(test_file)
        assert error is None

    def test_rejects_png_by_magic_bytes(self, safe_test_dir):
        """validate_file_type rejects PNG images by magic bytes."""
        test_file = safe_test_dir / "image.png"
        # Write PNG magic bytes
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        
        mime_type, error = validate_file_type(test_file)
        assert error is not None
        assert "binary" in error.lower()
        assert "PNG" in error

    def test_rejects_jpeg_by_magic_bytes(self, safe_test_dir):
        """validate_file_type rejects JPEG images by magic bytes."""
        test_file = safe_test_dir / "photo.jpg"
        test_file.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
        
        mime_type, error = validate_file_type(test_file)
        assert error is not None
        assert "binary" in error.lower()
        assert "JPEG" in error

    def test_rejects_pdf_by_magic_bytes(self, safe_test_dir):
        """validate_file_type rejects PDF documents by magic bytes."""
        test_file = safe_test_dir / "document.pdf"
        test_file.write_bytes(b"%PDF-1.4" + b"\x00" * 100)
        
        mime_type, error = validate_file_type(test_file)
        assert error is not None
        assert "binary" in error.lower()
        assert "PDF" in error

    def test_rejects_zip_by_magic_bytes(self, safe_test_dir):
        """validate_file_type rejects ZIP archives by magic bytes."""
        test_file = safe_test_dir / "archive.zip"
        test_file.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
        
        mime_type, error = validate_file_type(test_file)
        assert error is not None
        assert "binary" in error.lower()
        assert "ZIP" in error

    def test_rejects_exe_by_magic_bytes(self, safe_test_dir):
        """validate_file_type rejects executables by magic bytes."""
        test_file = safe_test_dir / "program.exe"
        test_file.write_bytes(b"MZ" + b"\x00" * 100)
        
        mime_type, error = validate_file_type(test_file)
        assert error is not None
        assert "binary" in error.lower()
        assert "executable" in error.lower()

    def test_rejects_unknown_extension(self, safe_test_dir):
        """validate_file_type rejects files with unknown extensions."""
        test_file = safe_test_dir / "unknown.xyz"
        test_file.write_text("unknown content")
        
        mime_type, error = validate_file_type(test_file)
        assert error is not None
        assert "unknown" in error.lower() or "not allowed" in error.lower()

    def test_read_tool_blocks_binary_files(self, read_file_tool, safe_test_dir):
        """ReadFileTool rejects binary files."""
        test_file = safe_test_dir / "binary.bin"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        
        result = read_file_tool.execute(path=str(test_file))
        assert result.success is False
        assert "binary" in result.error.lower()

    def test_read_tool_includes_mime_in_metadata(self, read_file_tool, safe_test_dir):
        """ReadFileTool includes MIME type in metadata."""
        test_file = safe_test_dir / "data.json"
        test_file.write_text('{"test": true}')
        
        result = read_file_tool.execute(path=str(test_file))
        assert result.success is True
        assert "mime_type" in result.metadata
        assert result.metadata["mime_type"] is not None

    def test_extension_fallback_works(self, safe_test_dir):
        """Extension fallback works when MIME detection fails."""
        # Create file with allowed extension but no standard MIME type
        test_file = safe_test_dir / "config.cfg"
        test_file.write_text("setting=value")
        
        mime_type, error = validate_file_type(test_file)
        assert error is None  # Should accept by extension
        assert "extension" in (mime_type or "").lower() or mime_type is not None

