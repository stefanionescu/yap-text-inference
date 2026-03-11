#!/usr/bin/env python
"""Reject subprocess calls that explicitly set shell=True."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import SRC_DIR, rel, report, parse_source, load_config_doc, iter_python_files  # noqa: E402

_RUNTIME_RULES = load_config_doc("rules", "runtime.toml")
_SUBPROCESS_RULE = _RUNTIME_RULES.get("no_shell_true_subprocess")
if not isinstance(_SUBPROCESS_RULE, dict):
    _SUBPROCESS_RULE = {}
SUBPROCESS_FUNCS = {
    str(value) for value in _SUBPROCESS_RULE.get("forbidden_functions", []) if isinstance(value, str)
} or {"run", "Popen", "call", "check_call", "check_output"}


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
