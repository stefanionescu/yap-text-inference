#!/usr/bin/env python
"""Require shell entrypoints to declare a bash shebang and strict mode."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared import report, load_config_doc  # noqa: E402
from shell.shared import rel, is_entrypoint, iter_target_shell_files  # noqa: E402

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_STRICT_MODE_RULE = _SHELL_RULES.get("strict_mode")
if not isinstance(_STRICT_MODE_RULE, dict):
    _STRICT_MODE_RULE = {}
SHEBANGS = {str(value) for value in _STRICT_MODE_RULE.get("shebangs", []) if isinstance(value, str)} or {
    "#!/usr/bin/env bash",
    "#!/bin/bash",
}
STRICT_MODE_LINE = str(_STRICT_MODE_RULE.get("required_line", "set -euo pipefail"))
STRICT_MODE_WINDOW = int(_STRICT_MODE_RULE.get("scan_window", 25))


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
