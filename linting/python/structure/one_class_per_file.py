#!/usr/bin/env python
"""Enforce one top-level non-dataclass class per runtime Python file."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from linting.repo import SRC_DIR, rel, report, load_config_doc, require_section, require_string_list
from linting.python.common import parse_source, iter_python_files

_STRUCTURE_RULES = load_config_doc("rules", "structure.toml")
_STRUCTURE_CONFIG_LABEL = "linting/config/rules/structure.toml"
_ONE_CLASS_RULE = require_section(_STRUCTURE_RULES, "one_class_per_file", _STRUCTURE_CONFIG_LABEL)
ALLOWLIST_RELATIVE_PATHS = set(
    require_string_list(_ONE_CLASS_RULE, "allowlist_relative_paths", f"{_STRUCTURE_CONFIG_LABEL} [one_class_per_file]")
)


def _is_dataclass_decorator(decorator: ast.expr) -> bool:
    target: ast.expr = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Name):
        return target.id == "dataclass"
    if isinstance(target, ast.Attribute):
        return target.attr == "dataclass"
    return False


def _is_dataclass_class(node: ast.ClassDef) -> bool:
    return any(_is_dataclass_decorator(decorator) for decorator in node.decorator_list)


def _collect_top_level_classes(filepath: Path) -> list[str]:
    result = parse_source(filepath)
    if result is None:
        return []
    _source, tree = result

    classes: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if _is_dataclass_class(node):
            continue
        classes.append(node.name)
    return classes


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(SRC_DIR):
        relative_path = py_file.relative_to(SRC_DIR).as_posix()
        if relative_path in ALLOWLIST_RELATIVE_PATHS:
            continue
        classes = _collect_top_level_classes(py_file)
        if len(classes) > 1:
            class_names = ", ".join(classes)
            violations.append(f"  {rel(py_file)}: {len(classes)} classes ({class_names})")

    return report("One non-dataclass-class-per-file violations", violations)


if __name__ == "__main__":
    sys.exit(main())
