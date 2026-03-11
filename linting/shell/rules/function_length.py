#!/usr/bin/env python
"""Enforce maximum code-line limits for shell functions."""

from __future__ import annotations

import sys
from linting.repo import report
from linting.shell.parser import violation, parse_functions, iter_analysis_files, function_length_limit


def main() -> int:
    limit = function_length_limit()
    violations: list[str] = []

    for shell_file in iter_analysis_files(sys.argv[1:]):
        for func in parse_functions(shell_file):
            size = func.code_line_count()
            if size > limit:
                violations.append(
                    violation(
                        shell_file,
                        func.lineno,
                        f"function `{func.name}` has {size} code lines (limit {limit})",
                    )
                )

    return report("Shell function-length violations", violations)


if __name__ == "__main__":
    sys.exit(main())
