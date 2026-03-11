#!/usr/bin/env python
"""Run all custom shell lint rules."""

from __future__ import annotations

import sys
import subprocess  # nosec B404
from linting.repo import load_config_doc

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_RUN_RULES = _SHELL_RULES.get("run")
if not isinstance(_RUN_RULES, dict):
    _RUN_RULES = {}
RULES = [str(rule_name) for rule_name in _RUN_RULES.get("rule_modules", []) if isinstance(rule_name, str)] or [
    "linting.shell.rules.strict_mode",
    "linting.shell.rules.disable_justification",
    "linting.shell.rules.docs",
]


def main() -> int:
    rule_args = sys.argv[1:]
    for rule in RULES:
        result = subprocess.run([sys.executable, "-m", rule, *rule_args], check=False)  # noqa: S603  # nosec
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
