#!/usr/bin/env python
"""Verify exact version pinning in Python requirements and root package.json."""

from __future__ import annotations

import sys
import json
from pathlib import Path
from linting.repo import ROOT, rel, report, require_string, load_config_doc, require_section, require_string_list

PACKAGE_JSON = ROOT / "package.json"
_INFRA_RULES = load_config_doc("rules", "infra.toml")
_INFRA_CONFIG_LABEL = "linting/config/rules/infra.toml"
_VERSION_PIN_RULE = require_section(_INFRA_RULES, "version_pins", _INFRA_CONFIG_LABEL)
_VERSION_PIN_LABEL = f"{_INFRA_CONFIG_LABEL} [version_pins]"
RANGE_PREFIXES = tuple(require_string_list(_VERSION_PIN_RULE, "range_prefixes", _VERSION_PIN_LABEL))
PIP_OPTION_PREFIXES = tuple(require_string_list(_VERSION_PIN_RULE, "pip_option_prefixes", _VERSION_PIN_LABEL))
SKIP_REQUIREMENT_PREFIXES = tuple(
    require_string_list(_VERSION_PIN_RULE, "skip_requirement_prefixes", _VERSION_PIN_LABEL)
)
EDITABLE_PREFIXES = tuple(require_string_list(_VERSION_PIN_RULE, "editable_prefixes", _VERSION_PIN_LABEL))
DIRECT_REFERENCE_SEPARATOR = require_string(_VERSION_PIN_RULE, "direct_reference_separator", _VERSION_PIN_LABEL)
PACKAGE_JSON_SECTIONS = tuple(require_string_list(_VERSION_PIN_RULE, "package_json_sections", _VERSION_PIN_LABEL))


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
        if not line or line.startswith("#") or line.startswith(SKIP_REQUIREMENT_PREFIXES):
            continue
        if line.startswith(PIP_OPTION_PREFIXES):
            continue
        if DIRECT_REFERENCE_SEPARATOR in line or line.startswith(EDITABLE_PREFIXES):
            continue
        if "==" not in line:
            violations.append(f"  {rel(path)}:{lineno} requirement must use exact == pin: {line}")


def _check_package_json(path: Path, violations: list[str]) -> None:
    if not path.exists():
        return

    package_doc = json.loads(path.read_text(encoding="utf-8"))
    for section in PACKAGE_JSON_SECTIONS:
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
