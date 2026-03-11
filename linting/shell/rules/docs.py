#!/usr/bin/env python
"""Require lightweight doc comments above shell functions in hooks/security scripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared import report, load_config_doc  # noqa: E402
from shell.shared import rel, iter_target_shell_files  # noqa: E402

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_DOC_RULE = _SHELL_RULES.get("docs")
if not isinstance(_DOC_RULE, dict):
    _DOC_RULE = {}
FUNCTION_RE = re.compile(str(_DOC_RULE.get("function_regex", r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{")))
DOC_RE = re.compile(str(_DOC_RULE.get("doc_regex", r"^#\s+[A-Za-z_][A-Za-z0-9_]*\s+[-:]\s+\S+")))
SCOPED_PREFIXES = tuple(str(value) for value in _DOC_RULE.get("scoped_prefixes", []) if isinstance(value, str)) or (
    ".githooks/",
    "linting/security/",
)
IGNORED_FUNCTION_NAMES = {
    str(value) for value in _DOC_RULE.get("ignored_function_names", []) if isinstance(value, str)
} or {"main"}


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

        for index, line in enumerate(lines):
            match = FUNCTION_RE.match(line)
            if not match:
                continue
            function_name = match.group(1)
            if function_name in IGNORED_FUNCTION_NAMES:
                continue

            previous = lines[index - 1].strip() if index > 0 else ""
            if not DOC_RE.match(previous):
                violations.append(
                    f"  {rel(shell_file)}:{index + 1} function `{function_name}` needs a doc comment above it"
                )

    return report("Shell function doc-comment violations", violations)


if __name__ == "__main__":
    sys.exit(main())
