#!/usr/bin/env python
"""Reject lazy singleton patterns in runtime Python modules."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import SRC_DIR, rel, report, parse_source, iter_python_files  # noqa: E402

SINGLETON_CLASS_SUFFIX = "Singleton"
SINGLETON_FN_NAMES = {"get_instance", "reset_instance"}
SINGLETON_STATE_NAMES = {"_STATE", "STATE", "_INSTANCE", "INSTANCE"}


def _top_level_targets(node: ast.Assign | ast.AnnAssign) -> list[str]:
    if isinstance(node, ast.AnnAssign):
        return [node.target.id] if isinstance(node.target, ast.Name) else []

    names: list[str] = []
    for target in node.targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
    return names


def _dict_contains_instance_key(value: ast.expr) -> bool:
    if not isinstance(value, ast.Dict):
        return False
    return any(isinstance(key, ast.Constant) and key.value == "instance" for key in value.keys)


def _is_lazy_singleton_state(node: ast.Assign | ast.AnnAssign) -> bool:
    names = _top_level_targets(node)
    if not names:
        return False

    value = node.value if isinstance(node, ast.AnnAssign) else node.value
    if value is None:
        return False

    if any(name in SINGLETON_STATE_NAMES for name in names) and _dict_contains_instance_key(value):
        return True

    if isinstance(value, ast.Constant) and value.value is None:
        return any(name.lower().endswith("_instance") for name in names)

    return False


def _collect_violations(filepath: Path) -> list[str]:
    result = parse_source(filepath)
    if result is None:
        return []
    _source, tree = result

    violations: list[str] = []
    r = rel(filepath)

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.endswith(SINGLETON_CLASS_SUFFIX):
            violations.append(f"  {r}:{node.lineno} class `{node.name}` uses singleton naming")
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in SINGLETON_FN_NAMES:
            violations.append(f"  {r}:{node.lineno} function `{node.name}` suggests singleton lifecycle")
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and _is_lazy_singleton_state(node):
            names = ", ".join(_top_level_targets(node))
            violations.append(f"  {r}:{node.lineno} lazy singleton module state assignment: {names}")

    return violations


def main() -> int:
    if not SRC_DIR.is_dir():
        print(f"[no-runtime-singletons] Missing source directory: {SRC_DIR}", file=sys.stderr)
        return 1

    violations: list[str] = []
    for py_file in iter_python_files(SRC_DIR):
        violations.extend(_collect_violations(py_file))

    return report("Runtime singleton pattern violations", violations)


if __name__ == "__main__":
    sys.exit(main())
