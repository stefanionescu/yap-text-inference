#!/usr/bin/env python
"""Disallow generic Python file, directory, and function names outside allowlisted paths."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from linting.python.common import parse_source, iter_python_files
from linting.repo import ROOT, SRC_DIR, TESTS_DIR, DOCKER_DIR, LINTING_DIR, rel, report, string_list, policy_section

_NAMING = policy_section("naming")
FORBIDDEN_EXACT = set(string_list(_NAMING.get("forbidden_exact")))
FORBIDDEN_PREFIXES = string_list(_NAMING.get("forbidden_prefixes"))
FORBIDDEN_SUFFIXES = string_list(_NAMING.get("forbidden_suffixes"))
FORBIDDEN_FUNCTION_NAMES = set(string_list(_NAMING.get("forbidden_function_names")))
ALLOWED_PATH_PREFIXES = string_list(_NAMING.get("allowed_path_prefixes"))


def _is_allowlisted(path: Path) -> bool:
    relative = rel(path)
    return any(relative == prefix or relative.startswith(f"{prefix}/") for prefix in ALLOWED_PATH_PREFIXES)


def _check_name(label: str, name: str, path: Path, violations: list[str]) -> None:
    if name in FORBIDDEN_EXACT:
        violations.append(f"  {rel(path)}: {label} `{name}` uses a forbidden generic name")
        return
    if any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        violations.append(f"  {rel(path)}: {label} `{name}` uses a forbidden generic prefix")
        return
    if any(name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        violations.append(f"  {rel(path)}: {label} `{name}` uses a forbidden generic suffix")


def _check_functions(path: Path, violations: list[str]) -> None:
    if _is_allowlisted(path) or rel(path).startswith("tests/"):
        return

    result = parse_source(path)
    if result is None:
        return

    _source, tree = result
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in FORBIDDEN_FUNCTION_NAMES:
            violations.append(f"  {rel(path)}:{node.lineno} function `{node.name}` uses a forbidden generic name")


def main() -> int:
    violations: list[str] = []
    scan_dirs = (SRC_DIR, TESTS_DIR, DOCKER_DIR, LINTING_DIR)

    for py_file in iter_python_files(*scan_dirs):
        if _is_allowlisted(py_file):
            continue

        relative_path = rel(py_file)

        if py_file.name != "__init__.py" and not (
            relative_path.startswith("tests/") and py_file.stem.startswith("test_")
        ):
            _check_name("file", py_file.stem, py_file, violations)

        for part in py_file.relative_to(ROOT).parts[:-1]:
            if part in FORBIDDEN_EXACT:
                violations.append(f"  {rel(py_file)}: parent directory `{part}` uses a forbidden generic name")
                break

        _check_functions(py_file, violations)

    return report("Generic naming violations", violations)


if __name__ == "__main__":
    sys.exit(main())
