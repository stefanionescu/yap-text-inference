#!/usr/bin/env python
"""Enforce a single conftest.py at the tests/ root.

This project uses one ``tests/conftest.py`` for custom collection.
Nested conftest files create fragmented fixture scoping and confuse
agents into duplicating setup logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import TESTS_DIR, rel, report  # noqa: E402

ALLOWED = TESTS_DIR / "conftest.py"


def main() -> int:
    violations: list[str] = []

    if not TESTS_DIR.is_dir():
        return 0

    for conftest in sorted(TESTS_DIR.rglob("conftest.py")):
        if conftest != ALLOWED:
            violations.append(f"  {rel(conftest)}: conftest.py only allowed at tests/conftest.py")

    return report("No-conftest-in-subfolders violations", violations)


if __name__ == "__main__":
    sys.exit(main())
