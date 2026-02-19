#!/usr/bin/env python
"""Enforce that unit test files live inside domain subfolders.

Tests must be at ``tests/unit/<domain>/foo.py``, never directly at
``tests/unit/foo.py``.  This keeps tests organized by domain and prevents
flat file accumulation.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIT_DIR = ROOT / "tests" / "unit"


def main() -> int:
    violations: list[str] = []

    if not UNIT_DIR.is_dir():
        return 0

    for child in sorted(UNIT_DIR.iterdir()):
        if child.is_file() and child.suffix == ".py" and child.name != "__init__.py":
            rel = child.relative_to(ROOT)
            violations.append(f"  {rel}: must be inside a domain subfolder (tests/unit/<domain>/)")

    if violations:
        print("Unit-test-domain-folders violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
