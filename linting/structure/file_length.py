#!/usr/bin/env python
"""Enforce maximum code-line limits per runtime file.

Python files in src/ must not exceed 300 code lines.
Shell scripts in scripts/ and docker/ must not exceed 300 code lines.

Blank lines, comment-only lines, and docstring-only lines are excluded from
the count. __init__.py barrel-export files (only imports and __all__) are exempt.
"""

from __future__ import annotations

import ast
import sys
import contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import (  # noqa: E402
    ROOT,
    SRC_DIR,
    SRC_FILE_LINES,
    SHELL_FILE_LINES,
    rel,
    report,
    comment_lines,
    docstring_lines,
    iter_python_files,
)

SCRIPTS_DIR = ROOT / "scripts"
DOCKER_DIR = ROOT / "docker"


def _is_barrel_init(filepath: Path) -> bool:
    """Check if __init__.py is a barrel-export file (only imports, __all__, docstrings, pass)."""
    if filepath.name != "__init__.py":
        return False
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if targets == ["__all__"]:
                continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.Pass):
            continue
        return False
    return True


def _count_code_lines(filepath: Path) -> int:
    """Count non-blank, non-comment, non-docstring lines."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0

    tree_result = None
    with contextlib.suppress(SyntaxError):
        tree_result = ast.parse(source)

    comments = comment_lines(filepath)
    docstrings = docstring_lines(tree_result) if tree_result else set()

    count = 0
    for i, line in enumerate(source.splitlines(), start=1):
        if not line.strip():
            continue
        if i in comments:
            continue
        if i in docstrings:
            continue
        count += 1
    return count


def _count_shell_code_lines(filepath: Path) -> int:
    """Count non-blank, non-comment lines for shell scripts."""
    try:
        raw_lines = filepath.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return 0

    count = 0
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(SRC_DIR):
        if _is_barrel_init(py_file):
            continue
        code_lines = _count_code_lines(py_file)
        if code_lines > SRC_FILE_LINES:
            violations.append(f"  {rel(py_file)}: {code_lines} code lines (limit {SRC_FILE_LINES})")

    for directory in (SCRIPTS_DIR, DOCKER_DIR):
        if not directory.is_dir():
            continue
        for sh_file in sorted(directory.rglob("*.sh")):
            code_lines = _count_shell_code_lines(sh_file)
            if code_lines > SHELL_FILE_LINES:
                violations.append(f"  {rel(sh_file)}: {code_lines} code lines (limit {SHELL_FILE_LINES})")

    return report("File length violations", violations)


if __name__ == "__main__":
    sys.exit(main())
