#!/usr/bin/env python
"""Detect repo-wide file/directory name-prefix collisions."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ROOT, MIN_PREFIX_COLLISION, rel, report, load_config_doc  # noqa: E402

_STRUCTURE_RULES = load_config_doc("rules", "structure.toml")
_PREFIX_RULE = _STRUCTURE_RULES.get("prefix_collisions")
if not isinstance(_PREFIX_RULE, dict):
    _PREFIX_RULE = {}

SCAN_ROOTS = [ROOT / str(value) for value in _PREFIX_RULE.get("scan_roots", []) if isinstance(value, str)] or [
    ROOT / "src",
    ROOT / "scripts",
    ROOT / "docker",
    ROOT / ".githooks",
    ROOT / "linting" / "config",
    ROOT / "linting" / "security",
    ROOT / "linting" / "testing",
]
IGNORED_PATHS = {
    str(value) for value in _PREFIX_RULE.get("ignored_paths", []) if isinstance(value, str)
} or {"linting/testing/__pycache__"}
IGNORED_NAMES = {
    str(value) for value in _PREFIX_RULE.get("ignored_names", []) if isinstance(value, str)
} or {"__pycache__", ".DS_Store"}
RESERVED_FILESET = {
    str(value) for value in _PREFIX_RULE.get("reserved_root_filenames", []) if isinstance(value, str)
} or {".githooks/pre-commit", ".githooks/pre-push", ".githooks/commit-msg"}


def _parse_scope(raw_args: list[str]) -> set[Path]:
    if not raw_args:
        return set()

    scoped_dirs: set[Path] = set()
    for raw_arg in raw_args:
        candidate = Path(raw_arg)
        resolved = candidate if candidate.is_absolute() else (ROOT / candidate).resolve()
        if not resolved.exists():
            continue
        scoped_dirs.add(resolved if resolved.is_dir() else resolved.parent)
    return scoped_dirs


def _stem(name: str) -> str:
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


def _prefix(name: str) -> str:
    stem = _stem(name)
    return re.split(r"[-_.]", stem, maxsplit=1)[0]


def _iter_directories(scope_dirs: set[Path]) -> list[Path]:
    directories: set[Path] = set()
    for root_dir in SCAN_ROOTS:
        if not root_dir.is_dir():
            continue
        directories.add(root_dir)
        directories.update(path for path in root_dir.rglob("*") if path.is_dir())

    if not scope_dirs:
        return sorted(directories)

    filtered: list[Path] = []
    for directory in sorted(directories):
        if any(directory == scope_dir or directory.is_relative_to(scope_dir) for scope_dir in scope_dirs):
            filtered.append(directory)
    return filtered


def _skip_path(path: Path) -> bool:
    relative = rel(path)
    return relative in IGNORED_PATHS or path.name in IGNORED_NAMES


def _reserved_group(directory: Path, names: list[str]) -> bool:
    relatives = {rel(directory / name) for name in names}
    return relatives.issubset(RESERVED_FILESET)


def main() -> int:
    scope_dirs = _parse_scope(sys.argv[1:])
    violations: list[str] = []

    for directory in _iter_directories(scope_dirs):
        if _skip_path(directory):
            continue

        prefix_groups: dict[str, list[str]] = defaultdict(list)
        for child in sorted(directory.iterdir()):
            if _skip_path(child):
                continue
            prefix_groups[_prefix(child.name)].append(child.name)

        for prefix, names in sorted(prefix_groups.items()):
            if len(names) < MIN_PREFIX_COLLISION:
                continue
            if _reserved_group(directory, names):
                continue
            joined = ", ".join(sorted(f"{name}/" if (directory / name).is_dir() else name for name in names))
            violations.append(f"  {rel(directory)}/: prefix `{prefix}` is shared by {joined}")

    return report("Prefix collision violations", violations)


if __name__ == "__main__":
    sys.exit(main())
