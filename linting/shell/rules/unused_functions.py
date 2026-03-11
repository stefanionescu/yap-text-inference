#!/usr/bin/env python
"""Detect shell functions that are defined but never referenced."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared import report, load_config_doc  # noqa: E402
from shell.parser import (  # noqa: E402
    violation,
    parse_functions,
    iter_usage_files,
    collect_used_tokens,
    iter_analysis_files,
    collect_function_allowlist,
)

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_UNUSED_RULE = _SHELL_RULES.get("unused_functions")
if not isinstance(_UNUSED_RULE, dict):
    _UNUSED_RULE = {}
IGNORED_FUNCTIONS = {
    str(value) for value in _UNUSED_RULE.get("ignored_function_names", []) if isinstance(value, str)
} or {"main"}


def main() -> int:
    target_files = iter_analysis_files(sys.argv[1:])
    if not target_files:
        return 0

    used_tokens = collect_used_tokens(iter_usage_files())
    violations: list[str] = []

    for shell_file in target_files:
        allow_all, allowed_names = collect_function_allowlist(shell_file)
        if allow_all:
            continue

        for func in parse_functions(shell_file):
            if func.name in IGNORED_FUNCTIONS or func.name in allowed_names:
                continue
            if func.name in used_tokens:
                continue
            violations.append(violation(shell_file, func.lineno, f"function `{func.name}` is never used"))

    return report("Unused shell-function violations", violations)


if __name__ == "__main__":
    sys.exit(main())
