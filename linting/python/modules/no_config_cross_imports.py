#!/usr/bin/env python
"""Enforce no sibling imports between config modules.

Config modules under src/config/ must not import from each other. Each
module should read its own env vars independently. Cross-imports create
fragile dependency chains and import-order issues.
"""

from __future__ import annotations

import ast
import sys
from linting.python.common import parse_source
from linting.repo import CONFIG_DIR, rel, report, load_config_doc, require_section, require_string_list

_MODULE_RULES = load_config_doc("rules", "modules.toml")
_MODULE_CONFIG_LABEL = "linting/config/rules/modules.toml"
_CROSS_IMPORT_RULE = require_section(_MODULE_RULES, "no_config_cross_imports", _MODULE_CONFIG_LABEL)
ALLOWLIST_FILENAMES = set(
    require_string_list(_CROSS_IMPORT_RULE, "allowlist_filenames", f"{_MODULE_CONFIG_LABEL} [no_config_cross_imports]")
)


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
