#!/usr/bin/env python
"""Enforce shell filename and parent-directory naming rules."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shell.shared import rel  # noqa: E402
from shared import report, policy_section  # noqa: E402
from shell.parser import violation, iter_analysis_files  # noqa: E402

_NAMING = policy_section("naming")
FORBIDDEN_EXACT = {str(value) for value in _NAMING.get("forbidden_exact", []) if isinstance(value, str)}
FORBIDDEN_PREFIXES = tuple(
    str(value) for value in _NAMING.get("forbidden_prefixes", []) if isinstance(value, str)
)
FORBIDDEN_SUFFIXES = tuple(
    str(value) for value in _NAMING.get("forbidden_suffixes", []) if isinstance(value, str)
)
ALLOWED_PATH_PREFIXES = tuple(
    str(value) for value in _NAMING.get("allowed_path_prefixes", []) if isinstance(value, str)
)


def _allowed(path: Path) -> bool:
    relative = rel(path)
    return any(relative == prefix or relative.startswith(f"{prefix}/") for prefix in ALLOWED_PATH_PREFIXES)


def _stem(path: Path) -> str:
    if path.suffix == ".sh":
        return path.stem
    return path.name


def _check_name(value: str, kind: str) -> str | None:
    if value in FORBIDDEN_EXACT:
        return f"{kind} `{value}` uses a forbidden generic name"
    for prefix in FORBIDDEN_PREFIXES:
        if value.startswith(prefix):
            return f"{kind} `{value}` uses a forbidden generic prefix `{prefix}`"
    for suffix in FORBIDDEN_SUFFIXES:
        if value.endswith(suffix):
            return f"{kind} `{value}` uses a forbidden generic suffix `{suffix}`"
    return None


def main() -> int:
    violations: list[str] = []

    for shell_file in iter_analysis_files(sys.argv[1:]):
        if _allowed(shell_file):
            continue

        stem_error = _check_name(_stem(shell_file), "filename")
        if stem_error:
            violations.append(violation(shell_file, None, stem_error))

        parent = shell_file.parent.name
        parent_error = _check_name(parent, "parent directory")
        if parent_error:
            violations.append(violation(shell_file, None, parent_error))

    return report("Shell naming violations", violations)


if __name__ == "__main__":
    sys.exit(main())
