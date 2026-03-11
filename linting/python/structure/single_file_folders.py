#!/usr/bin/env python
"""Detect repo directories that only contain a single file and no subdirectories."""

from __future__ import annotations

import sys
from pathlib import Path
from linting.repo import ROOT, rel, report, load_config_doc

_STRUCTURE_RULES = load_config_doc("rules", "structure.toml")
_SINGLE_RULE = _STRUCTURE_RULES.get("single_file_folders")
if not isinstance(_SINGLE_RULE, dict):
    _SINGLE_RULE = {}

SCAN_ROOTS = [ROOT / str(value) for value in _SINGLE_RULE.get("scan_roots", []) if isinstance(value, str)] or [
    ROOT / "src",
    ROOT / "scripts",
    ROOT / "docker",
    ROOT / ".githooks",
    ROOT / "linting" / "config",
    ROOT / "linting" / "licenses",
    ROOT / "linting" / "rules" / "python",
    ROOT / "linting" / "security",
]
ALLOWLIST = {str(value) for value in _SINGLE_RULE.get("allowlist_relative_paths", []) if isinstance(value, str)} or {
    "docker/vllm/download",
    ".githooks/.jscpd",
    "linting/licenses",
    "linting/python/naming",
    "linting/security/bearer",
    "linting/security/gitleaks",
    "linting/security/pip_audit",
    "linting/security/trivy",
}
IGNORED_NAMES = {str(value) for value in _SINGLE_RULE.get("ignored_names", []) if isinstance(value, str)} or {
    "__pycache__",
    ".DS_Store",
}


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


def _should_skip_directory(directory: Path, relative: str) -> bool:
    return relative in ALLOWLIST or directory == ROOT or directory.name in IGNORED_NAMES


def _visible_children(directory: Path) -> tuple[list[Path], list[Path]]:
    files = [child for child in directory.iterdir() if child.is_file() and child.name not in IGNORED_NAMES]
    subdirs = [child for child in directory.iterdir() if child.is_dir() and child.name not in IGNORED_NAMES]
    return files, subdirs


def main() -> int:
    scope_dirs = _parse_scope(sys.argv[1:])
    violations: list[str] = []

    for directory in _iter_directories(scope_dirs):
        relative = rel(directory)
        if _should_skip_directory(directory, relative):
            continue

        files, subdirs = _visible_children(directory)
        if len(files) == 1 and not subdirs:
            violations.append(f"  {relative}/ has only {files[0].name} — flatten or regroup related code")

    return report("Single-file folder violations", violations)


if __name__ == "__main__":
    sys.exit(main())
