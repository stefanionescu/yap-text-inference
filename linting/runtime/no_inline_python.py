#!/usr/bin/env python
"""Detect inline Python usage inside shell scripts.

Flags lines in .sh files that invoke Python inline via ``python -c``,
``python3 -c``, heredocs (``python <<``), or ``$PYTHON_EXEC -c`` variants.
All Python logic should live in proper modules called with ``python -m``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ROOT, rel, report  # noqa: E402

# Patterns that indicate inline Python in bash (applied to stripped, non-comment lines)
INLINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpython3?\s+-c\b"),
    re.compile(r"\bpython3?\s+<<"),
    re.compile(r"\$\{?PYTHON_EXEC\}?\s+-c\b"),
    re.compile(r"\$\{?PYTHON_EXEC\}?\s+<<"),
)


def _is_comment(line: str) -> bool:
    """Return True if *line* is a shell comment (ignoring leading whitespace)."""
    return line.lstrip().startswith("#")


def main() -> int:
    violations: list[str] = []

    for sh_file in sorted(ROOT.rglob("*.sh")):
        try:
            lines = sh_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(lines, start=1):
            if _is_comment(line):
                continue
            for pattern in INLINE_PATTERNS:
                if pattern.search(line):
                    violations.append(f"  {rel(sh_file)}:{lineno}: {line.strip()}")
                    break  # one match per line is enough

    return report("Inline Python in shell scripts (use python -m instead)", violations)


if __name__ == "__main__":
    sys.exit(main())
