#!/usr/bin/env python
"""Enforce top-level import grouping: single-line imports first.

Rules are applied within each contiguous top-level import run:
- ``from __future__`` imports must come first.
- At most one blank line is allowed between the ``__future__`` block and
  non-future imports.
- Non-future single-line imports must be contiguous (no blank lines).
- Non-future multi-line imports must appear after non-future single-line imports.
- Non-future single-line imports must be sorted by length, then alphabetically.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ROOT, rel, report, parse_source, iter_python_files  # noqa: E402

TARGET_DIRS = ("src", "tests", "linting")


@dataclass(frozen=True)
class ImportEntry:
    node: ast.Import | ast.ImportFrom
    text: str
    is_future: bool
    is_single_line: bool


def _is_import_stmt(node: ast.stmt) -> bool:
    return isinstance(node, ast.Import | ast.ImportFrom)


def _build_import_runs(body: list[ast.stmt]) -> list[list[ast.Import | ast.ImportFrom]]:
    runs: list[list[ast.Import | ast.ImportFrom]] = []
    current: list[ast.Import | ast.ImportFrom] = []

    for stmt in body:
        if _is_import_stmt(stmt):
            current.append(stmt)
            continue
        if current:
            runs.append(current)
            current = []

    if current:
        runs.append(current)

    return runs


def _statement_text(source: str, source_lines: list[str], node: ast.Import | ast.ImportFrom) -> str:
    segment = ast.get_source_segment(source, node)
    if segment is not None:
        return segment.strip()

    start = node.lineno - 1
    end = (node.end_lineno or node.lineno) - 1
    return "\n".join(source_lines[start : end + 1]).strip()


def _blank_lines_between(source_lines: list[str], first: ast.stmt, second: ast.stmt) -> int:
    start = first.end_lineno or first.lineno
    end = second.lineno - 1
    if end <= start:
        return 0
    return sum(1 for line in source_lines[start:end] if not line.strip())


def _preview(text: str, limit: int = 96) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _single_line_sort_key(entry: ImportEntry) -> tuple[int, str]:
    normalized = " ".join(entry.text.split())
    return (len(normalized), normalized)


def _collect_run_violations(path: Path, source_lines: list[str], entries: list[ImportEntry]) -> list[str]:
    violations: list[str] = []
    rel_path = rel(path)

    first_non_future_index = next((idx for idx, entry in enumerate(entries) if not entry.is_future), None)
    if first_non_future_index is None:
        return violations

    for entry in entries[first_non_future_index:]:
        if not entry.is_future:
            continue
        violations.append(
            f"  {rel_path}:{entry.node.lineno} __future__ imports must appear before all other imports"
        )

    if first_non_future_index > 0:
        last_future = entries[first_non_future_index - 1]
        first_non_future = entries[first_non_future_index]
        blank_lines = _blank_lines_between(source_lines, last_future.node, first_non_future.node)
        if blank_lines > 1:
            violations.append(
                f"  {rel_path}:{first_non_future.node.lineno} allow at most one blank line after __future__ imports"
            )

    non_future_entries = [entry for entry in entries if not entry.is_future]

    saw_multiline = False
    for entry in non_future_entries:
        if entry.is_single_line:
            if saw_multiline:
                violations.append(
                    f"  {rel_path}:{entry.node.lineno} single-line import appears after a multi-line import"
                )
                break
            continue
        saw_multiline = True

    for previous, current in zip(non_future_entries, non_future_entries[1:], strict=False):
        if not previous.is_single_line or not current.is_single_line:
            continue
        blank_lines = _blank_lines_between(source_lines, previous.node, current.node)
        if blank_lines > 0:
            violations.append(
                f"  {rel_path}:{current.node.lineno} single-line imports must be contiguous (remove blank lines)"
            )

    single_line_entries = [entry for entry in non_future_entries if entry.is_single_line]
    expected_order = sorted(single_line_entries, key=_single_line_sort_key)
    for actual, expected in zip(single_line_entries, expected_order, strict=False):
        if actual is expected:
            continue
        violations.append(
            f"  {rel_path}:{actual.node.lineno} single-line imports must be ordered by length then alphabetically "
            f"(expected `{_preview(expected.text)}` before `{_preview(actual.text)}`)"
        )
        break

    return violations


def _collect_file_violations(path: Path) -> list[str]:
    result = parse_source(path)
    if result is None:
        return []
    source, tree = result
    source_lines = source.splitlines()

    violations: list[str] = []
    for run in _build_import_runs(tree.body):
        entries: list[ImportEntry] = []
        for node in run:
            text = _statement_text(source, source_lines, node)
            entries.append(
                ImportEntry(
                    node=node,
                    text=text,
                    is_future=isinstance(node, ast.ImportFrom) and node.module == "__future__",
                    is_single_line=node.lineno == (node.end_lineno or node.lineno),
                )
            )

        violations.extend(_collect_run_violations(path, source_lines, entries))

    return violations


def main() -> int:
    scan_dirs = [ROOT / d for d in TARGET_DIRS]
    violations: list[str] = []

    for py_file in iter_python_files(*scan_dirs):
        violations.extend(_collect_file_violations(py_file))

    return report("Single-line-imports-first violations", violations)


if __name__ == "__main__":
    sys.exit(main())
