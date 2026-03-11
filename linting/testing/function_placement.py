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

from shared import TESTS_DIR, rel, report, parse_source, load_config_doc, iter_python_files  # noqa: E402

_TESTING_RULES = load_config_doc("rules", "testing.toml")
_PLACEMENT_RULE = _TESTING_RULES.get("test_function_placement")
if not isinstance(_PLACEMENT_RULE, dict):
    _PLACEMENT_RULE = {}
ALLOWED_SUITE_DIRS = {
    str(value) for value in _PLACEMENT_RULE.get("allowed_suite_dirs", []) if isinstance(value, str)
} or {"unit", "integration", "e2e"}
_MIN_SUITE_PATH_PARTS = 3


def _is_allowed_suite(path: Path) -> bool:
    return (
        len(path.parts) >= _MIN_SUITE_PATH_PARTS and path.parts[0] == "suites" and path.parts[1] in ALLOWED_SUITE_DIRS
    )


def _iter_test_functions(tree: ast.Module) -> list[tuple[str, int]]:
    return [
        (node.name, node.lineno)
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_")
    ]


def _collect_file_violations(py_file: Path) -> list[str]:
    rel_to_tests = py_file.relative_to(TESTS_DIR)
    if _is_allowed_suite(rel_to_tests):
        return []

    result = parse_source(py_file)
    if result is None:
        return []
    _source, tree = result

    return [
        f"  {rel(py_file)}: def {name}() (line {lineno}) — test functions belong in tests/suites/"
        for name, lineno in _iter_test_functions(tree)
    ]


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(TESTS_DIR):
        if py_file.name == "__init__.py":
            continue
        violations.extend(_collect_file_violations(py_file))

    return report("Test-function-placement violations", violations)


if __name__ == "__main__":
    sys.exit(main())
