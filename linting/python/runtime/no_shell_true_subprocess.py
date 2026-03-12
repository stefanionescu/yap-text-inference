#!/usr/bin/env python
"""Reject subprocess calls that explicitly set shell=True."""

from __future__ import annotations

import ast
import sys
from linting.repo import SRC_DIR, rel, report, load_config_doc, require_section, require_string_list
from linting.python.common import parse_source, iter_python_files

_RUNTIME_RULES = load_config_doc("rules", "runtime.toml")
_RUNTIME_CONFIG_LABEL = "linting/config/rules/runtime.toml"
_SUBPROCESS_RULE = require_section(_RUNTIME_RULES, "no_shell_true_subprocess", _RUNTIME_CONFIG_LABEL)
SUBPROCESS_FUNCS = set(
    require_string_list(_SUBPROCESS_RULE, "forbidden_functions", f"{_RUNTIME_CONFIG_LABEL} [no_shell_true_subprocess]")
)


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(SRC_DIR):
        result = parse_source(py_file)
        if result is None:
            continue

        _source, tree = result
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in SUBPROCESS_FUNCS:
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "subprocess":
                continue

            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    violations.append(f"  {rel(py_file)}:{node.lineno} subprocess.{node.func.attr}(..., shell=True)")

    return report("subprocess shell=True violations", violations)


if __name__ == "__main__":
    sys.exit(main())
