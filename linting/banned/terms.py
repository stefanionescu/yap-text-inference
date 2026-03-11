#!/usr/bin/env python
"""Scan tracked text files for banned repository terminology."""

from __future__ import annotations

import re
import sys
import json
from pathlib import Path
from linting.repo import ROOT, rel, report

CONFIG_PATH = ROOT / "linting" / "config" / "language" / "banned-terms.json"


def _load_config() -> tuple[re.Pattern[str], dict[str, object]]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    banned_terms = [str(term).strip() for term in config.get("bannedTerms", []) if str(term).strip()]
    if not banned_terms:
        raise ValueError("bannedTerms must be non-empty")
    alternation = "|".join(sorted((re.escape(term) for term in banned_terms), key=len, reverse=True))
    flags = re.IGNORECASE if config.get("matching", {}).get("caseInsensitive") else 0
    return re.compile(rf"\b(?:{alternation})\b", flags), config


def _should_skip(path: Path, config: dict[str, object]) -> bool:
    normalized = f"/{rel(path).replace('\\', '/')}"
    exclusions = config.get("exclusions", {})
    if not isinstance(exclusions, dict):
        return False

    for segment in exclusions.get("pathContains", []):
        if isinstance(segment, str) and segment in normalized:
            return True

    basename_equals = {value for value in exclusions.get("basenameEquals", []) if isinstance(value, str)}
    if path.name in basename_equals:
        return True

    extension_equals = {value for value in exclusions.get("extensionEquals", []) if isinstance(value, str)}
    return path.suffix.lower() in extension_equals


def _tracked_dirs(config: dict[str, object]) -> list[Path]:
    raw_dirs = config.get("trackedDirs", [])
    if isinstance(raw_dirs, list):
        tracked = [ROOT / str(value) for value in raw_dirs if isinstance(value, str)]
        if tracked:
            return tracked
    return [
        ROOT / "src",
        ROOT / "tests",
        ROOT / "scripts",
        ROOT / "docker",
        ROOT / "linting",
        ROOT / ".githooks",
    ]


def _iter_target_files(args: list[str], config: dict[str, object]) -> list[Path]:
    if not args:
        files: list[Path] = []
        for root_dir in _tracked_dirs(config):
            if not root_dir.exists():
                continue
            for path in sorted(root_dir.rglob("*")):
                if path.is_file():
                    files.append(path)
        return files

    files = []
    for raw in args:
        candidate = Path(raw)
        resolved = candidate if candidate.is_absolute() else (ROOT / candidate).resolve()
        if resolved.is_file():
            files.append(resolved)
    return sorted(set(files))


def main() -> int:
    pattern, config = _load_config()
    violations: list[str] = []

    for path in _iter_target_files(sys.argv[1:], config):
        if _should_skip(path, config):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            match = pattern.search(line)
            if match:
                violations.append(f"  {rel(path)}:{lineno} banned term `{match.group(0)}`")
                break

    return report("Banned terminology violations", violations)


if __name__ == "__main__":
    sys.exit(main())
