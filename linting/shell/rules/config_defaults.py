#!/usr/bin/env python
"""Confine shell env-default assignments to approved config/default files."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from linting.repo import load_config_doc, report, require_int, require_section, require_string_list
from linting.shell.shared import rel, is_entrypoint
from linting.shell.parser import violation, iter_analysis_files

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_SHELL_CONFIG_LABEL = "linting/config/rules/shell.toml"
_DEFAULT_RULE = require_section(_SHELL_RULES, "config_defaults", _SHELL_CONFIG_LABEL)
_DEFAULT_RULE_LABEL = f"{_SHELL_CONFIG_LABEL} [config_defaults]"

ALLOWED_PREFIXES = tuple(require_string_list(_DEFAULT_RULE, "allowed_path_prefixes", _DEFAULT_RULE_LABEL))
ALLOWED_FILES = set(require_string_list(_DEFAULT_RULE, "allowed_files", _DEFAULT_RULE_LABEL))
SCOPED_PREFIXES = tuple(require_string_list(_DEFAULT_RULE, "scoped_prefixes", _DEFAULT_RULE_LABEL))
SCAN_WINDOW = require_int(_DEFAULT_RULE, "scan_window", _DEFAULT_RULE_LABEL)

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
                    "self-defaulting env assignment for "
                    f"`{match.group('lhs')}` belongs in an approved config/default file",
                )
            )

    return report("Shell config-default violations", violations)


if __name__ == "__main__":
    sys.exit(main())
