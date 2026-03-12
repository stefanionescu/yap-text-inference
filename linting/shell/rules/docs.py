#!/usr/bin/env python
"""Require lightweight doc comments above shell functions in hooks/security scripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from linting.shell.shared import rel, iter_target_shell_files
from linting.repo import report, require_string, load_config_doc, require_section, require_string_list

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_SHELL_CONFIG_LABEL = "linting/config/rules/shell.toml"
_DOC_RULE = require_section(_SHELL_RULES, "docs", _SHELL_CONFIG_LABEL)
_DOC_RULE_LABEL = f"{_SHELL_CONFIG_LABEL} [docs]"
FUNCTION_RE = re.compile(require_string(_DOC_RULE, "function_regex", _DOC_RULE_LABEL))
DOC_RE = re.compile(require_string(_DOC_RULE, "doc_regex", _DOC_RULE_LABEL))
SCOPED_PREFIXES = tuple(require_string_list(_DOC_RULE, "scoped_prefixes", _DOC_RULE_LABEL))
IGNORED_FUNCTION_NAMES = set(require_string_list(_DOC_RULE, "ignored_function_names", _DOC_RULE_LABEL))


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
