#!/usr/bin/env python
"""Enforce test_ prefix on runnable test filenames.

All runnable tests live under ``tests/suites/`` and must follow standard pytest
discovery naming (``test_*.py``).
"""

from __future__ import annotations

import sys
from linting.python.common import iter_python_files
from linting.repo import TESTS_DIR, rel, report, load_config_doc, require_section, require_string_list

_TESTING_RULES = load_config_doc("rules", "testing.toml")
_TESTING_CONFIG_LABEL = "linting/config/rules/testing.toml"
_PREFIX_RULE = require_section(_TESTING_RULES, "test_file_prefix", _TESTING_CONFIG_LABEL)
SCAN_DIRS = [
    TESTS_DIR.parent / raw_dir
    for raw_dir in require_string_list(_PREFIX_RULE, "scan_dirs", f"{_TESTING_CONFIG_LABEL} [test_file_prefix]")
]


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
