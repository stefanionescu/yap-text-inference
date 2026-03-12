#!/usr/bin/env python
"""Require shellcheck disable directives in hooks/security scripts to explain themselves."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from linting.repo import load_config_doc, report, require_section, require_string, require_string_list
from linting.shell.shared import rel, iter_target_shell_files

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_SHELL_CONFIG_LABEL = "linting/config/rules/shell.toml"
_DISABLE_RULE = require_section(_SHELL_RULES, "disable_justification", _SHELL_CONFIG_LABEL)
_DISABLE_RULE_LABEL = f"{_SHELL_CONFIG_LABEL} [disable_justification]"
DISABLE_RE = re.compile(require_string(_DISABLE_RULE, "disable_regex", _DISABLE_RULE_LABEL))
JUSTIFICATION_RE = re.compile(require_string(_DISABLE_RULE, "justification_regex", _DISABLE_RULE_LABEL))
_REQUIRED_COMMENT_PARTS = 3
SCOPED_PREFIXES = tuple(require_string_list(_DISABLE_RULE, "scoped_prefixes", _DISABLE_RULE_LABEL))


def _in_scope(path: Path) -> bool:
    relative = rel(path)
    return any(relative.startswith(prefix) for prefix in SCOPED_PREFIXES)


def main() -> int:
    violations: list[str] = []
    for shell_file in iter_target_shell_files(sys.argv[1:]):
        if not _in_scope(shell_file):
            continue

        try:
            lines = shell_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(lines, start=1):
            if not DISABLE_RE.search(line):
                continue
            comment_parts = line.split("#", 2)
            if len(comment_parts) >= _REQUIRED_COMMENT_PARTS and JUSTIFICATION_RE.search(f"#{comment_parts[2]}"):
                continue
            violations.append(
                "  "
                f"{rel(shell_file)}:{lineno} shellcheck disable directives "
                "in hooks/security scripts need justification"
            )

    return report("Shellcheck disable justification violations", violations)


if __name__ == "__main__":
    sys.exit(main())
