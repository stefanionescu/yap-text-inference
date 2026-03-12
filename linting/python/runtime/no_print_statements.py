#!/usr/bin/env python
"""Reject runtime print statements outside approved CLI-style modules."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from linting.python.common import parse_source, iter_python_files
from linting.repo import SRC_DIR, rel, report, load_config_doc, require_section, require_string_list

_RUNTIME_RULES = load_config_doc("rules", "runtime.toml")
_RUNTIME_CONFIG_LABEL = "linting/config/rules/runtime.toml"
_PRINT_RULE = require_section(_RUNTIME_RULES, "no_print_statements", _RUNTIME_CONFIG_LABEL)
_PRINT_RULE_LABEL = f"{_RUNTIME_CONFIG_LABEL} [no_print_statements]"
ALLOWED_PREFIXES = tuple(require_string_list(_PRINT_RULE, "allowed_prefixes", _PRINT_RULE_LABEL))
ALLOWED_EXACT_PATHS = set(require_string_list(_PRINT_RULE, "allowed_exact_paths", _PRINT_RULE_LABEL))


def _is_allowed(path: Path) -> bool:
    relative = rel(path)
    return relative in ALLOWED_EXACT_PATHS or any(relative.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(SRC_DIR):
        if _is_allowed(py_file):
            continue

        result = parse_source(py_file)
        if result is None:
            continue

        _source, tree = result
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                violations.append(f"  {rel(py_file)}:{node.lineno} print() is only allowed in CLI-style modules")

    return report("Runtime print() violations", violations)


if __name__ == "__main__":
    sys.exit(main())
