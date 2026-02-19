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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import SRC_DIR, rel, report, parse_source, iter_python_files  # noqa: E402


def _check_file(filepath: Path) -> str | None:
    result = parse_source(filepath)
    if result is None:
        return None
    _source, tree = result

    last_public_line: int | None = None
    last_public_name: str | None = None

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        if node.name.startswith("_"):
            if last_public_line is not None:
                return (
                    f"  {rel(filepath)}: private {node.name}() at line {node.lineno} "
                    f"appears after public {last_public_name}() at line {last_public_line}"
                )
        else:
            last_public_line = node.lineno
            last_public_name = node.name

    return None


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(SRC_DIR):
        violation = _check_file(py_file)
        if violation:
            violations.append(violation)

    return report("Function-order violations (private before public)", violations)


if __name__ == "__main__":
    sys.exit(main())
