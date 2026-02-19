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

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "src" / "config"


def _config_module_names() -> set[str]:
    """Return the stem names of all config modules (excluding __init__)."""
    if not CONFIG_DIR.is_dir():
        return set()
    return {
        p.stem
        for p in CONFIG_DIR.glob("*.py")
        if p.name != "__init__.py"
    }


def main() -> int:
    sibling_names = _config_module_names()
    violations: list[str] = []

    for py_file in sorted(CONFIG_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        try:
            source = py_file.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue

            module = node.module or ""

            # Relative import from sibling: from .deploy import ...
            if node.level == 1 and module in sibling_names:
                rel = py_file.relative_to(ROOT)
                violations.append(
                    f"  {rel}: from .{module} import ... (line {node.lineno})"
                )

    if violations:
        print("No-config-cross-imports violations (config/ must not import siblings):", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
