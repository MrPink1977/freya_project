#!/usr/bin/env python3
"""Find Python functions and methods missing docstrings.

Scans the freya package for functions and methods without docstrings
and generates a report.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


class DocstringChecker(ast.NodeVisitor):
    """AST visitor to find functions/methods without docstrings."""

    def __init__(self, filename: str):
        self.filename = filename
        self.missing: List[Tuple[str, int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        if not ast.get_docstring(node):
            # Skip private functions (starting with _) unless they're __init__
            if not node.name.startswith("_") or node.name == "__init__":
                self.missing.append((self.filename, node.lineno, node.name))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        if not ast.get_docstring(node):
            if not node.name.startswith("_") or node.name == "__init__":
                self.missing.append((self.filename, node.lineno, node.name))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        if not ast.get_docstring(node):
            # Skip private classes
            if not node.name.startswith("_"):
                self.missing.append((self.filename, node.lineno, f"class {node.name}"))
        self.generic_visit(node)


def check_file(filepath: Path) -> List[Tuple[str, int, str]]:
    """Check a Python file for missing docstrings.

    Args:
        filepath: Path to Python file to check.

    Returns:
        List of (filename, line_number, function_name) tuples for missing docstrings.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        checker = DocstringChecker(str(filepath))
        checker.visit(tree)
        return checker.missing
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def main():
    """Main entry point."""
    freya_dir = Path(__file__).parent.parent / "freya"

    if not freya_dir.exists():
        print(f"Error: {freya_dir} does not exist", file=sys.stderr)
        return 1

    # Find all Python files
    python_files = list(freya_dir.rglob("*.py"))

    all_missing = []
    for filepath in sorted(python_files):
        # Skip __pycache__ and test files
        if "__pycache__" in str(filepath) or "test_" in filepath.name:
            continue

        missing = check_file(filepath)
        all_missing.extend(missing)

    # Group by file
    by_file = {}
    for filename, lineno, funcname in all_missing:
        if filename not in by_file:
            by_file[filename] = []
        by_file[filename].append((lineno, funcname))

    # Print report
    print(f"Found {len(all_missing)} functions/methods/classes missing docstrings:\n")

    for filename in sorted(by_file.keys()):
        print(f"\n{filename}:")
        for lineno, funcname in sorted(by_file[filename]):
            print(f"  Line {lineno:4d}: {funcname}")

    print(f"\n\nTotal: {len(all_missing)} missing docstrings")
    print(f"Files affected: {len(by_file)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
