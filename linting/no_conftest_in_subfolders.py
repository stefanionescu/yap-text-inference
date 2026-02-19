#!/usr/bin/env python
"""Enforce a single conftest.py at the tests/ root.

This project uses one ``tests/conftest.py`` for custom collection.
Nested conftest files create fragmented fixture scoping and confuse
agents into duplicating setup logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
ALLOWED = TESTS_DIR / "conftest.py"


def main() -> int:
    violations: list[str] = []

    if not TESTS_DIR.is_dir():
        return 0

    for conftest in sorted(TESTS_DIR.rglob("conftest.py")):
        if conftest != ALLOWED:
            rel = conftest.relative_to(ROOT)
            violations.append(f"  {rel}: conftest.py only allowed at tests/conftest.py")

    if violations:
        print("No-conftest-in-subfolders violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
