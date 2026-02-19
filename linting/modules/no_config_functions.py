#!/usr/bin/env python
"""Enforce no function definitions in config modules.

Config modules under src/config/ must be purely declarative (constants + env
reads). Function definitions belong in helpers/ or other runtime modules.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import CONFIG_DIR, rel, report, parse_source  # noqa: E402


def main() -> int:
    violations: list[str] = []

    if not CONFIG_DIR.is_dir():
        return 0

    for py_file in sorted(CONFIG_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        result = parse_source(py_file)
        if result is None:
            continue
        _source, tree = result

        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                violations.append(f"  {rel(py_file)}: def {node.name}() (line {node.lineno})")

    return report("No-config-functions violations (config/ must be declarative)", violations)


if __name__ == "__main__":
    sys.exit(main())
