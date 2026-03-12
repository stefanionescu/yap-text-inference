#!/usr/bin/env python
"""Enforce that test functions only live in tests/suites/*.

Files under tests/support/ are support modules (fixtures, payloads, runners)
and must not contain ``def test_*`` functions.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from linting.repo import TESTS_DIR, rel, report, load_config_doc, require_section, require_string_list
from linting.python.common import parse_source, iter_python_files

_TESTING_RULES = load_config_doc("rules", "testing.toml")
_TESTING_CONFIG_LABEL = "linting/config/rules/testing.toml"
_PLACEMENT_RULE = require_section(_TESTING_RULES, "test_function_placement", _TESTING_CONFIG_LABEL)
ALLOWED_SUITE_DIRS = set(
    require_string_list(_PLACEMENT_RULE, "allowed_suite_dirs", f"{_TESTING_CONFIG_LABEL} [test_function_placement]")
)
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
