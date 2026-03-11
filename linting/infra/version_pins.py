#!/usr/bin/env python
"""Verify exact version pinning in Python requirements and root package.json."""

from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ROOT, rel, report, load_config_doc  # noqa: E402

RANGE_PREFIXES = ("^", "~", ">", "<", "*")
PACKAGE_JSON = ROOT / "package.json"
PIP_OPTION_PREFIXES = (
    "--extra-index-url",
    "--index-url",
    "--find-links",
    "--trusted-host",
)


def _requirement_files(violations: list[str]) -> list[Path]:
    config_doc = load_config_doc("repo", "files.toml")
    raw_values = config_doc.get("requirement_files")
    if not isinstance(raw_values, list):
        violations.append("  linting/config/repo/files.toml: `requirement_files` must be a list")
        return []

    paths: list[Path] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            violations.append("  linting/config/repo/files.toml: `requirement_files` entries must be strings")
            continue
        paths.append(ROOT / raw_value)
    return paths


def _check_requirements(path: Path, violations: list[str]) -> None:
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(("-r", "--requirement", "-c", "--constraint")):
            continue
        if line.startswith(PIP_OPTION_PREFIXES):
            continue
        if " @" in line or line.startswith(("-e", "--editable")):
            continue
        if "==" not in line:
            violations.append(f"  {rel(path)}:{lineno} requirement must use exact == pin: {line}")


def _check_package_json(path: Path, violations: list[str]) -> None:
    if not path.exists():
        return

    package_doc = json.loads(path.read_text(encoding="utf-8"))
    for section in ("dependencies", "devDependencies"):
        values = package_doc.get(section, {})
        if not isinstance(values, dict):
            continue
        for name, version in sorted(values.items()):
            if not isinstance(version, str):
                violations.append(f"  {rel(path)}: {section}.{name} must use a string version")
                continue
            if version.startswith(RANGE_PREFIXES):
                violations.append(f"  {rel(path)}: {section}.{name} must use an exact version, found {version}")


def main() -> int:
    violations: list[str] = []

    for req_file in _requirement_files(violations):
        _check_requirements(req_file, violations)
    _check_package_json(PACKAGE_JSON, violations)

    return report("Version pin violations", violations)


if __name__ == "__main__":
    sys.exit(main())
