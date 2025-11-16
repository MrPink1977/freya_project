"""Test that verifies the package installation works correctly."""
import os
import sys


def test_freya_package_exists():
    """Test that freya package can be found in the project."""
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # This should work if packaging is set up correctly
    import freya
    assert freya is not None


def test_freya_tools_package_exists():
    """Test that freya.tools subpackage can be found."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    import freya.tools
    assert freya.tools is not None


def test_package_metadata_files_exist():
    """Test that required packaging files exist."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check for pyproject.toml
    pyproject_path = os.path.join(project_root, 'pyproject.toml')
    assert os.path.exists(pyproject_path), "pyproject.toml should exist"
    
    # Check for setup.cfg
    setup_cfg_path = os.path.join(project_root, 'setup.cfg')
    assert os.path.exists(setup_cfg_path), "setup.cfg should exist"
    
    # Check for MANIFEST.in
    manifest_path = os.path.join(project_root, 'MANIFEST.in')
    assert os.path.exists(manifest_path), "MANIFEST.in should exist"


def test_pyproject_toml_content():
    """Test that pyproject.toml has required fields."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject_path = os.path.join(project_root, 'pyproject.toml')
    
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Check for essential sections
    assert '[build-system]' in content
    assert '[project]' in content
    assert 'name = "freya"' in content
    assert 'version = "0.1.0"' in content
    assert '[tool.setuptools]' in content
