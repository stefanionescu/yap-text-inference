#!/usr/bin/env python
"""Enforce test_ prefix on runnable test filenames.

All runnable tests live under ``tests/suites/`` and must follow standard pytest
discovery naming (``test_*.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import TESTS_DIR, rel, report, iter_python_files  # noqa: E402

SCAN_DIRS = [TESTS_DIR / "suites"]


def main() -> int:
    violations: list[str] = []

    for py_file in iter_python_files(*SCAN_DIRS):
        if py_file.name == "__init__.py":
            continue
        if not py_file.name.startswith("test_"):
            violations.append(f"  {rel(py_file)}: filename must use test_ prefix")

    return report("Test-file-prefix violations (tests/suites must use test_*)", violations)


if __name__ == "__main__":
    sys.exit(main())
