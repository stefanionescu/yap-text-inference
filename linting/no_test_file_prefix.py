#!/usr/bin/env python
"""Enforce no test_ prefix on test filenames.

This project uses non-prefixed filenames (e.g. ``sampling_validation.py``,
not ``test_sampling_validation.py``) with custom pytest collection in
``tests/conftest.py``.  Files under ``tests/unit/`` and ``tests/integration/``
must not start with ``test_``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
SCAN_DIRS = [TESTS_DIR / "unit", TESTS_DIR / "integration"]


def main() -> int:
    violations: list[str] = []

    for scan_dir in SCAN_DIRS:
        if not scan_dir.is_dir():
            continue
        for py_file in sorted(scan_dir.rglob("*.py")):
            if py_file.name.startswith("test_"):
                rel = py_file.relative_to(ROOT)
                violations.append(f"  {rel}: filename must not use test_ prefix")

    if violations:
        print("No-test-file-prefix violations (use plain names, not test_*):", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
