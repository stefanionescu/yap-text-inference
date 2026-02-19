#!/usr/bin/env python
"""Enforce maximum function length for runtime Python modules.

Checks functions and methods under src/ and fails when any function exceeds
60 code lines, excluding blank lines, comment-only lines, and docstrings.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import SRC_DIR, FUNCTION_LINES, rel, report, comment_lines, docstring_lines, iter_python_files  # noqa: E402


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self._scope: list[str] = []
        self.functions: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._collect_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._collect_function(node)

    def _collect_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualified = ".".join((*self._scope, node.name)) if self._scope else node.name
        self.functions.append((qualified, node))
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()


def _count_function_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    raw_lines: list[str],
    comments: set[int],
    docstrings: set[int],
) -> int:
    count = 0
    for line_no in range(node.lineno, node.end_lineno + 1):
        if line_no in comments or line_no in docstrings:
            continue
        line = raw_lines[line_no - 1] if line_no - 1 < len(raw_lines) else ""
        if not line.strip():
            continue
        count += 1
    return count


def _collect_violations(filepath: Path) -> list[str]:
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    comments = comment_lines(filepath)
    docstrings_set = docstring_lines(tree)
    raw_lines = source.splitlines()

    collector = _FunctionCollector()
    collector.visit(tree)

    violations: list[str] = []
    for qualified, node in collector.functions:
        size = _count_function_lines(node, raw_lines, comments, docstrings_set)
        if size > FUNCTION_LINES:
            violations.append(
                f"  {rel(filepath)}:{node.lineno} {qualified} -> {size} code lines (limit {FUNCTION_LINES})"
            )
    return violations


def main() -> int:
    violations: list[str] = []
    for py_file in iter_python_files(SRC_DIR):
        violations.extend(_collect_violations(py_file))

    return report("Function length violations", violations)


if __name__ == "__main__":
    sys.exit(main())
