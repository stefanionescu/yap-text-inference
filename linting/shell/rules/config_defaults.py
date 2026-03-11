#!/usr/bin/env python
"""Confine shell env-default assignments to approved config/default files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared import report, load_config_doc  # noqa: E402
from shell.shared import rel, is_entrypoint  # noqa: E402
from shell.parser import violation, iter_analysis_files  # noqa: E402

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_DEFAULT_RULE = _SHELL_RULES.get("config_defaults")
if not isinstance(_DEFAULT_RULE, dict):
    _DEFAULT_RULE = {}

ALLOWED_PREFIXES = tuple(
    str(value) for value in _DEFAULT_RULE.get("allowed_path_prefixes", []) if isinstance(value, str)
)
ALLOWED_FILES = {str(value) for value in _DEFAULT_RULE.get("allowed_files", []) if isinstance(value, str)}
SCOPED_PREFIXES = tuple(
    str(value) for value in _DEFAULT_RULE.get("scoped_prefixes", []) if isinstance(value, str)
) or ("scripts/", "docker/")
SCAN_WINDOW = int(_DEFAULT_RULE.get("scan_window", 80))

DEFAULT_ASSIGN_RE = re.compile(
    r'^\s*(?:export\s+|local\s+)?(?P<lhs>[A-Z_][A-Z0-9_]*)="?\$\{(?P<rhs>[A-Z_][A-Z0-9_]*)[:-][^}]*\}"?\s*$'
)


def _allowed(path: Path) -> bool:
    relative = rel(path)
    if relative in ALLOWED_FILES:
        return True
    return any(relative == prefix or relative.startswith(f"{prefix}/") for prefix in ALLOWED_PREFIXES)


def _in_scope(path: Path) -> bool:
    relative = rel(path)
    return is_entrypoint(path) and any(relative.startswith(prefix) for prefix in SCOPED_PREFIXES)


def main() -> int:
    violations: list[str] = []

    for shell_file in iter_analysis_files(sys.argv[1:]):
        if not _in_scope(shell_file) or _allowed(shell_file):
            continue

        try:
            lines = shell_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(lines[:SCAN_WINDOW], start=1):
            if line.lstrip().startswith("#"):
                continue
            match = DEFAULT_ASSIGN_RE.match(line.strip())
            if not match:
                continue
            violations.append(
                violation(
                    shell_file,
                    lineno,
                    f"self-defaulting env assignment for `{match.group('lhs')}` belongs in an approved config/default file",
                )
            )

    return report("Shell config-default violations", violations)


if __name__ == "__main__":
    sys.exit(main())
