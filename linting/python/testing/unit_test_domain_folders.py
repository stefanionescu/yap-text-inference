#!/usr/bin/env python
"""Enforce that unit test files live inside domain subfolders.

Tests must be at ``tests/suites/unit/<domain>/test_foo.py``, never directly at
``tests/suites/unit/test_foo.py``.  This keeps tests organized by domain and prevents
flat file accumulation.
"""

from __future__ import annotations

import sys
from linting.repo import ROOT, rel, report

UNIT_DIR = ROOT / "tests" / "suites" / "unit"


def main() -> int:
    violations: list[str] = []

    if not UNIT_DIR.is_dir():
        return 0

    for child in sorted(UNIT_DIR.iterdir()):
        if child.is_file() and child.suffix == ".py" and child.name != "__init__.py":
            violations.append(f"  {rel(child)}: must be inside a domain subfolder (tests/suites/unit/<domain>/)")

    return report("Unit-test-domain-folders violations", violations)


if __name__ == "__main__":
    sys.exit(main())
