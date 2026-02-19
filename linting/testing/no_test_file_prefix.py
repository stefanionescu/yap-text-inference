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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import TESTS_DIR, rel, report, iter_python_files  # noqa: E402

SCAN_DIRS = [TESTS_DIR / "unit", TESTS_DIR / "integration"]


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(*SCAN_DIRS):
        if py_file.name.startswith("test_"):
            violations.append(f"  {rel(py_file)}: filename must not use test_ prefix")

    return report("No-test-file-prefix violations (use plain names, not test_*)", violations)


if __name__ == "__main__":
    sys.exit(main())
