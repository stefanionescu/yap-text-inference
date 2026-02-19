#!/usr/bin/env python
"""Enforce no function definitions in config modules.

Config modules under src/config/ must be purely declarative (constants + env
reads). Function definitions belong in helpers/ or other runtime modules.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "src" / "config"


def main() -> int:
    violations: list[str] = []

    if not CONFIG_DIR.is_dir():
        return 0

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
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                rel = py_file.relative_to(ROOT)
                violations.append(f"  {rel}: def {node.name}() (line {node.lineno})")

    if violations:
        print("No-config-functions violations (config/ must be declarative):", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
