#!/usr/bin/env python
"""Enforce that test functions only live in tests/unit/ and tests/integration/.

Files under tests/helpers/, tests/config/, tests/messages/, tests/prompts/,
tests/state/, tests/logic/, and tests/e2e/ are support modules (fixtures,
payloads, runners).  They must not contain ``def test_*`` functions.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
ALLOWED_DIRS = {"unit", "integration"}


def main() -> int:
    violations: list[str] = []

    if not TESTS_DIR.is_dir():
        return 0

    for py_file in sorted(TESTS_DIR.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue

        # Determine the top-level subdirectory under tests/
        rel = py_file.relative_to(TESTS_DIR)
        top_dir = rel.parts[0] if len(rel.parts) > 1 else None

        if top_dir in ALLOWED_DIRS:
            continue

        try:
            source = py_file.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_"):
                rel_from_root = py_file.relative_to(ROOT)
                violations.append(
                    f"  {rel_from_root}: def {node.name}() (line {node.lineno}) — "
                    f"test functions belong in tests/unit/ or tests/integration/"
                )

    if violations:
        print("Test-function-placement violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
