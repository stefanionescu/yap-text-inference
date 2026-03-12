#!/usr/bin/env python
"""Reject legacy/backward-compatibility markers in runtime modules."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from linting.repo import ROOT, rel, report, load_config_doc, require_section, require_string_list

_RUNTIME_RULES = load_config_doc("rules", "runtime.toml")
_RUNTIME_CONFIG_LABEL = "linting/config/rules/runtime.toml"
_LEGACY_RULE = require_section(_RUNTIME_RULES, "no_legacy_markers", _RUNTIME_CONFIG_LABEL)
_LEGACY_RULE_LABEL = f"{_RUNTIME_CONFIG_LABEL} [no_legacy_markers]"
TARGETS = [ROOT / value for value in require_string_list(_LEGACY_RULE, "targets", _LEGACY_RULE_LABEL)]
ALLOWLIST = {ROOT / value for value in require_string_list(_LEGACY_RULE, "allowlist", _LEGACY_RULE_LABEL)}
PATTERNS = [
    re.compile(value, re.IGNORECASE)
    for value in require_string_list(_LEGACY_RULE, "patterns", _LEGACY_RULE_LABEL)
]


def _iter_target_files() -> list[Path]:
    files: list[Path] = []
    for target in TARGETS:
        if target.is_file():
            files.append(target)
            continue
        if target.is_dir():
            for py in sorted(target.rglob("*.py")):
                if "__pycache__" not in py.parts:
                    files.append(py)
    return files


def _collect_violations(path: Path) -> list[str]:
    if path in ALLOWLIST:
        return []
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []
    r = rel(path)
    for idx, line in enumerate(text.splitlines(), start=1):
        for pattern in PATTERNS:
            if pattern.search(line):
                violations.append(f"  {r}:{idx} contains prohibited marker `{pattern.pattern}`")
                break
    return violations


def main() -> int:
    violations: list[str] = []
    for py_file in _iter_target_files():
        violations.extend(_collect_violations(py_file))

    return report("Legacy/compatibility marker violations", violations)


if __name__ == "__main__":
    sys.exit(main())
