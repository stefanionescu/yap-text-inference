#!/usr/bin/env python
"""Enforce private-before-public function ordering.

Within each source file, all _-prefixed top-level functions must appear
before all non-_-prefixed top-level functions. Only checks top-level
FunctionDef/AsyncFunctionDef, not methods or nested functions.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"


def _check_file(filepath: Path) -> str | None:
    try:
        source = filepath.read_text()
    except (OSError, UnicodeDecodeError):
        return None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    last_public_line: int | None = None
    last_public_name: str | None = None

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        if node.name.startswith("_"):
            if last_public_line is not None:
                rel = filepath.relative_to(ROOT)
                return (
                    f"  {rel}: private {node.name}() at line {node.lineno} "
                    f"appears after public {last_public_name}() at line {last_public_line}"
                )
        else:
            last_public_line = node.lineno
            last_public_name = node.name

    return None


def main() -> int:
    violations: list[str] = []

    if SRC_DIR.is_dir():
        for py_file in sorted(SRC_DIR.rglob("*.py")):
            violation = _check_file(py_file)
            if violation:
                violations.append(violation)

    if violations:
        print("Function-order violations (private before public):", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
