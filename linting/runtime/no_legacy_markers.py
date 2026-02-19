#!/usr/bin/env python
"""Reject legacy/backward-compatibility markers in runtime modules."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ROOT, rel, report  # noqa: E402

TARGETS = [
    ROOT / "src" / "runtime",
    ROOT / "src" / "messages",
    ROOT / "src" / "handlers",
    ROOT / "src" / "execution",
    ROOT / "src" / "server.py",
]

ALLOWLIST = {
    ROOT / "src" / "execution" / "compat.py",
}

PATTERNS = [
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
