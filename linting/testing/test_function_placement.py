#!/usr/bin/env python
"""Enforce that test functions only live in tests/suites/*.

Files under tests/support/ are support modules (fixtures, payloads, runners)
and must not contain ``def test_*`` functions.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import TESTS_DIR, rel, report, parse_source, iter_python_files  # noqa: E402

ALLOWED_SUITE_DIRS = {"unit", "integration", "e2e"}


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(TESTS_DIR):
        if py_file.name == "__init__.py":
            continue

        # Determine the top-level subdirectory under tests/
        rel_to_tests = py_file.relative_to(TESTS_DIR)
        top_dir = rel_to_tests.parts[0] if len(rel_to_tests.parts) > 1 else None

        if top_dir == "suites" and len(rel_to_tests.parts) > 2 and rel_to_tests.parts[1] in ALLOWED_SUITE_DIRS:
            continue

        result = parse_source(py_file)
        if result is None:
            continue
        _source, tree = result

        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_"):
                violations.append(
                    f"  {rel(py_file)}: def {node.name}() (line {node.lineno}) — "
                    f"test functions belong in tests/suites/"
                )

    return report("Test-function-placement violations", violations)


if __name__ == "__main__":
    sys.exit(main())
