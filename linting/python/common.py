"""Shared AST and file helpers for custom Python lint rules."""

from __future__ import annotations

import ast
import tokenize
from pathlib import Path


def iter_python_files(*dirs: Path) -> list[Path]:
    """Return sorted .py files under *dirs*, skipping ``__pycache__``."""
    files: list[Path] = []
    for directory in dirs:
        if not directory.is_dir():
            continue
        for py_file in sorted(directory.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            files.append(py_file)
    return files


def parse_source(filepath: Path) -> tuple[str, ast.Module] | None:
    """Read and parse a Python file, returning ``(source, tree)`` or ``None``."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return None

    return source, tree


def comment_lines(filepath: Path) -> set[int]:
    """Return 1-based line numbers that are comment-only lines."""
    comments: set[int] = set()
    try:
        with filepath.open("rb") as file_obj:
            for token in tokenize.tokenize(file_obj.readline):
                if token.type == tokenize.COMMENT:
                    comments.add(token.start[0])
    except tokenize.TokenError:
        pass
    return comments


def docstring_lines(tree: ast.AST) -> set[int]:
    """Return 1-based line numbers occupied by module/class/function docstrings."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if not getattr(node, "body", None):
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        if not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        end_lineno = first.end_lineno or first.lineno
        for line_no in range(first.lineno, end_lineno + 1):
            lines.add(line_no)
    return lines
