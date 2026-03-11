#!/usr/bin/env python
"""Run all custom shell lint rules."""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "linting"))

from shared import load_config_doc  # noqa: E402

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_RUN_RULES = _SHELL_RULES.get("run")
if not isinstance(_RUN_RULES, dict):
    _RUN_RULES = {}
RULES = [ROOT / str(rule_path) for rule_path in _RUN_RULES.get("rule_modules", []) if isinstance(rule_path, str)] or [
    ROOT / "linting" / "shell" / "rules" / "strict_mode.py",
    ROOT / "linting" / "shell" / "rules" / "disable_justification.py",
    ROOT / "linting" / "shell" / "rules" / "docs.py",
]


def main() -> int:
    rule_args = sys.argv[1:]
    for rule in RULES:
        result = subprocess.run([sys.executable, str(rule), *rule_args], check=False)  # noqa: S603
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
