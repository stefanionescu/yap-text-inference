#!/usr/bin/env python
"""Enforce no sibling imports between config modules.

Config modules under src/config/ must not import from each other. Each
module should read its own env vars independently. Cross-imports create
fragile dependency chains and import-order issues.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import CONFIG_DIR, rel, report, parse_source, load_config_doc  # noqa: E402

_MODULE_RULES = load_config_doc("rules", "modules.toml")
_CROSS_IMPORT_RULE = _MODULE_RULES.get("no_config_cross_imports")
if not isinstance(_CROSS_IMPORT_RULE, dict):
    _CROSS_IMPORT_RULE = {}
ALLOWLIST_FILENAMES = {
    str(value) for value in _CROSS_IMPORT_RULE.get("allowlist_filenames", []) if isinstance(value, str)
} or {
    "engine.py",
    "gpu.py",
    "limits.py",
    "trt.py",
}


def _config_module_names() -> set[str]:
    """Return the stem names of all config modules (excluding __init__)."""
    if not CONFIG_DIR.is_dir():
        return set()
    return {p.stem for p in CONFIG_DIR.glob("*.py") if p.name != "__init__.py"}


def main() -> int:
    sibling_names = _config_module_names()
    violations: list[str] = []

    for py_file in sorted(CONFIG_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if py_file.name in ALLOWLIST_FILENAMES:
            continue

        result = parse_source(py_file)
        if result is None:
            continue
        _source, tree = result

        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue

            module = node.module or ""

            # Relative import from sibling: from .deploy import ...
            if node.level == 1 and module in sibling_names:
                violations.append(f"  {rel(py_file)}: from .{module} import ... (line {node.lineno})")

    return report("No-config-cross-imports violations (config/ must not import siblings)", violations)


if __name__ == "__main__":
    sys.exit(main())
