#!/usr/bin/env python
"""Require shell entrypoints to declare a bash shebang and strict mode."""

from __future__ import annotations

import sys
from linting.shell.shared import rel, is_entrypoint, iter_target_shell_files
from linting.repo import report, require_int, require_string, load_config_doc, require_section, require_string_list

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_SHELL_CONFIG_LABEL = "linting/config/rules/shell.toml"
_STRICT_MODE_RULE = require_section(_SHELL_RULES, "strict_mode", _SHELL_CONFIG_LABEL)
_STRICT_MODE_LABEL = f"{_SHELL_CONFIG_LABEL} [strict_mode]"
SHEBANGS = set(require_string_list(_STRICT_MODE_RULE, "shebangs", _STRICT_MODE_LABEL))
STRICT_MODE_LINE = require_string(_STRICT_MODE_RULE, "required_line", _STRICT_MODE_LABEL)
STRICT_MODE_WINDOW = require_int(_STRICT_MODE_RULE, "scan_window", _STRICT_MODE_LABEL)


def main() -> int:
    violations: list[str] = []

    for shell_file in iter_target_shell_files(sys.argv[1:]):
        if not is_entrypoint(shell_file):
            continue
        try:
            lines = shell_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        if not lines or lines[0].strip() not in SHEBANGS:
            violations.append(f"  {rel(shell_file)}: missing bash shebang")
            continue

        head_window = lines[1:STRICT_MODE_WINDOW]
        if not any(line.strip() == STRICT_MODE_LINE for line in head_window):
            violations.append(f"  {rel(shell_file)}: missing `set -euo pipefail` near the top of the file")

    return report("Shell strict-mode violations", violations)


if __name__ == "__main__":
    sys.exit(main())
