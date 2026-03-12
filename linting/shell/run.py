#!/usr/bin/env python
"""Run all custom shell lint rules."""

from __future__ import annotations

import sys
import subprocess  # nosec B404
from linting.repo import load_config_doc, require_section, require_string_list

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_SHELL_CONFIG_LABEL = "linting/config/rules/shell.toml"
_RUN_RULES = require_section(_SHELL_RULES, "run", _SHELL_CONFIG_LABEL)
RULES = require_string_list(_RUN_RULES, "rule_modules", f"{_SHELL_CONFIG_LABEL} [run]")


def main() -> int:
    rule_args = sys.argv[1:]
    for rule in RULES:
        result = subprocess.run([sys.executable, "-m", rule, *rule_args], check=False)  # noqa: S603  # nosec
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
