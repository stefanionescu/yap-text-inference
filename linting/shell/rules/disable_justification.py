#!/usr/bin/env python
"""Require shellcheck disable directives in hooks/security scripts to explain themselves."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared import report, load_config_doc  # noqa: E402
from shell.shared import rel, iter_target_shell_files  # noqa: E402

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_DISABLE_RULE = _SHELL_RULES.get("disable_justification")
if not isinstance(_DISABLE_RULE, dict):
    _DISABLE_RULE = {}
DISABLE_RE = re.compile(str(_DISABLE_RULE.get("disable_regex", r"^\s*#\s*shellcheck\s+disable=")))
JUSTIFICATION_RE = re.compile(str(_DISABLE_RULE.get("justification_regex", r"#\s*.+")))
_REQUIRED_COMMENT_PARTS = 3
SCOPED_PREFIXES = tuple(str(value) for value in _DISABLE_RULE.get("scoped_prefixes", []) if isinstance(value, str)) or (
    ".githooks/",
    "linting/security/",
)


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
