#!/usr/bin/env python
"""Parsing helpers shared by custom shell lint rules."""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass
from shared import SHELL_FUNCTION_LINES
from shell.shared import rel, iter_all_shell_files, iter_target_shell_files

FUNCTION_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{")
TOKEN_RE = re.compile(r"(?:^|[;|&(){}\s])([A-Za-z_][A-Za-z0-9_]*)\b")


@dataclass(frozen=True)
class ShellFunction:
    """Metadata for a parsed shell function block."""

    path: Path
    name: str
    lineno: int
    end_lineno: int
    lines: tuple[str, ...]

    def code_line_count(self) -> int:
        """Count non-blank, non-comment lines inside the function body."""
        count = 0
        for line in self.lines:
            stripped = strip_comments(line).strip()
            if not stripped or stripped == "}":
                continue
            count += 1
        return count


def iter_analysis_files(raw_paths: list[str] | None = None) -> list[Path]:
    """Return the target files for direct violations plus the full shell corpus."""
    return iter_target_shell_files(raw_paths)


def iter_usage_files() -> list[Path]:
    """Return the full shell corpus used for cross-file reference scans."""
    return iter_all_shell_files()


def _starts_parameter_expansion(line: str, index: int, in_single: bool, in_double: bool) -> bool:
    return not in_single and line[index] == "$" and index + 1 < len(line) and line[index + 1] == "{"


def _toggles_single_quote(char: str, in_double: bool) -> bool:
    return not in_double and char == "'"


def _toggles_double_quote(char: str, in_single: bool) -> bool:
    return not in_single and char == '"'


def _is_comment_start(char: str, in_single: bool, in_double: bool, parameter_depth: int) -> bool:
    return not in_single and not in_double and parameter_depth == 0 and char == "#"


def strip_comments(line: str) -> str:
    """Remove shell comments while respecting quoted strings and escapes."""
    result: list[str] = []
    in_single = False
    in_double = False
    escaped = False
    parameter_depth = 0
    index = 0
    while index < len(line):
        char = line[index]
        if escaped:
            result.append(char)
            escaped = False
            index += 1
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            index += 1
            continue
        if _toggles_single_quote(char, in_double):
            in_single = not in_single
            result.append(char)
            index += 1
            continue
        if _toggles_double_quote(char, in_single):
            in_double = not in_double
            result.append(char)
            index += 1
            continue
        if _starts_parameter_expansion(line, index, in_single, in_double):
            parameter_depth += 1
            result.extend(["$", "{"])
            index += 2
            continue
        if parameter_depth > 0 and char == "}":
            parameter_depth -= 1
            result.append(char)
            index += 1
            continue
        if _is_comment_start(char, in_single, in_double, parameter_depth):
            break
        result.append(char)
        index += 1
    return "".join(result)


def brace_delta(line: str) -> int:
    """Return the net opening brace count for the given line."""
    stripped = strip_comments(line)
    return stripped.count("{") - stripped.count("}")


def parse_functions(path: Path) -> list[ShellFunction]:
    """Parse shell function blocks from *path*."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    functions: list[ShellFunction] = []
    index = 0
    while index < len(lines):
        match = FUNCTION_RE.match(lines[index])
        if not match:
            index += 1
            continue

        end_index = index
        balance = brace_delta(lines[end_index])
        while balance > 0 and end_index + 1 < len(lines):
            end_index += 1
            balance += brace_delta(lines[end_index])

        functions.append(
            ShellFunction(
                path=path,
                name=match.group(1),
                lineno=index + 1,
                end_lineno=end_index + 1,
                lines=tuple(lines[index : end_index + 1]),
            )
        )
        index = end_index + 1

    return functions


def collect_function_allowlist(path: Path) -> tuple[bool, set[str]]:
    """Return file-wide and per-function lint allow directives for *path*."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False, set()

    allow_all = any("lint:allow-unused-functions" in line for line in lines)
    allowed_names: set[str] = set()
    for line in lines:
        match = re.search(r"lint:allow-unused-function\s+([A-Za-z_][A-Za-z0-9_]*)", line)
        if match:
            allowed_names.add(match.group(1))
    return allow_all, allowed_names


def collect_used_tokens(paths: list[Path]) -> set[str]:
    """Collect shell-like identifier tokens from *paths* outside function declarations."""
    used: set[str] = set()
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for line in lines:
            stripped = strip_comments(line).strip()
            if not stripped:
                continue
            match = FUNCTION_RE.match(stripped)
            if match:
                stripped = stripped[stripped.find("{") + 1 :].strip()
            if not stripped:
                continue
            for token in TOKEN_RE.findall(f" {stripped}"):
                used.add(token)
    return used


def function_length_limit() -> int:
    """Return the configured shell function length limit."""
    return SHELL_FUNCTION_LINES


def violation(path: Path, lineno: int | None, message: str) -> str:
    """Format a shell-rule violation string."""
    if lineno is None:
        return f"  {rel(path)}: {message}"
    return f"  {rel(path)}:{lineno} {message}"
