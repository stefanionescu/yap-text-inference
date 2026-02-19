#!/usr/bin/env python
"""Enforce that unit test files live inside domain subfolders.

Tests must be at ``tests/unit/<domain>/foo.py``, never directly at
``tests/unit/foo.py``.  This keeps tests organized by domain and prevents
flat file accumulation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ROOT, rel, report  # noqa: E402

UNIT_DIR = ROOT / "tests" / "unit"


def main() -> int:
    violations: list[str] = []

    if not UNIT_DIR.is_dir():
        return 0

    for child in sorted(UNIT_DIR.iterdir()):
        if child.is_file() and child.suffix == ".py" and child.name != "__init__.py":
            violations.append(f"  {rel(child)}: must be inside a domain subfolder (tests/unit/<domain>/)")

    return report("Unit-test-domain-folders violations", violations)


if __name__ == "__main__":
    sys.exit(main())
