#!/usr/bin/env python
"""Reject lazy module loading/export patterns in runtime Python modules."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from linting.python.common import parse_source, iter_python_files
from linting.repo import SRC_DIR, rel, report, load_config_doc, require_section, require_string_list

_IMPORT_RULES = load_config_doc("rules", "imports.toml")
_IMPORT_CONFIG_LABEL = "linting/config/rules/imports.toml"
_LAZY_LOADING_RULE = require_section(_IMPORT_RULES, "no_lazy_module_loading", _IMPORT_CONFIG_LABEL)
FORBIDDEN_EXPORT_HOOKS = set(
    require_string_list(
        _LAZY_LOADING_RULE,
        "forbidden_export_hooks",
        f"{_IMPORT_CONFIG_LABEL} [no_lazy_module_loading]",
    )
)


def _collect_violations(path: Path) -> list[str]:
    result = parse_source(path)
    if result is None:
        return []
    _source, tree = result

    r = rel(path)
    violations: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in FORBIDDEN_EXPORT_HOOKS:
            violations.append(f"  {r}:{node.lineno} forbidden lazy export hook `{node.name}`")

    for walk_node in ast.walk(tree):
        if not isinstance(walk_node, ast.Call):
            continue
        func = walk_node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "importlib"
            and func.attr == "import_module"
        ):
            violations.append(f"  {r}:{walk_node.lineno} forbidden dynamic import via importlib.import_module")
        if isinstance(func, ast.Name) and func.id == "import_module":
            violations.append(f"  {r}:{walk_node.lineno} forbidden dynamic import via import_module")

    if path.name == "__init__.py":
        for parent in ast.walk(tree):
            if not isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for inner_node in ast.walk(parent):
                if isinstance(inner_node, ast.Import | ast.ImportFrom):
                    violations.append(f"  {r}:{inner_node.lineno} local import in __init__.py is forbidden")
    return violations


def main() -> int:
    if not SRC_DIR.is_dir():
        print(f"[no-lazy-module-loading] Missing source directory: {SRC_DIR}", file=sys.stderr)
        return 1

    violations: list[str] = []
    for py_file in iter_python_files(SRC_DIR):
        violations.extend(_collect_violations(py_file))

    return report("Lazy module loading/export violations", violations)


if __name__ == "__main__":
    sys.exit(main())
