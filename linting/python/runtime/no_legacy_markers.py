#!/usr/bin/env python
"""Reject legacy/backward-compatibility markers in runtime modules."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from linting.repo import ROOT, rel, report, load_config_doc

_RUNTIME_RULES = load_config_doc("rules", "runtime.toml")
_LEGACY_RULE = _RUNTIME_RULES.get("no_legacy_markers")
if not isinstance(_LEGACY_RULE, dict):
    _LEGACY_RULE = {}
TARGETS = [ROOT / str(value) for value in _LEGACY_RULE.get("targets", []) if isinstance(value, str)] or [
    ROOT / "src" / "runtime",
    ROOT / "src" / "messages",
    ROOT / "src" / "handlers",
    ROOT / "src" / "execution",
    ROOT / "src" / "server.py",
]

ALLOWLIST = {ROOT / str(value) for value in _LEGACY_RULE.get("allowlist", []) if isinstance(value, str)} or {
    ROOT / "src" / "execution" / "compat.py",
}

PATTERNS = [
    re.compile(str(value), re.IGNORECASE) for value in _LEGACY_RULE.get("patterns", []) if isinstance(value, str)
] or [
    re.compile(r"\blegacy\b", re.IGNORECASE),
    re.compile(r"\bdeprecated\b", re.IGNORECASE),
    re.compile(r"\bworkaround\b", re.IGNORECASE),
    re.compile(r"\bbackward(?:\s|-)?compat(?:ible|ibility)\b", re.IGNORECASE),
    re.compile(r"\bcompatibility\b", re.IGNORECASE),
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
