#!/usr/bin/env python
"""Enforce test_ prefix on runnable test filenames.

All runnable tests live under ``tests/suites/`` and must follow standard pytest
discovery naming (``test_*.py``).
"""

from __future__ import annotations

import sys
from linting.python.common import iter_python_files
from linting.repo import TESTS_DIR, rel, report, load_config_doc

_TESTING_RULES = load_config_doc("rules", "testing.toml")
_PREFIX_RULE = _TESTING_RULES.get("test_file_prefix")
if not isinstance(_PREFIX_RULE, dict):
    _PREFIX_RULE = {}
SCAN_DIRS = [
    TESTS_DIR.parent / str(raw_dir) for raw_dir in _PREFIX_RULE.get("scan_dirs", []) if isinstance(raw_dir, str)
] or [TESTS_DIR / "suites"]


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
