#!/usr/bin/env python
"""Validate repo-local lint/security configuration references."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared import ROOT, rel, report, policy_section, load_config_doc  # noqa: E402


def _configured_paths(field: str, violations: list[str]) -> list[Path]:
    config_doc = load_config_doc("repo", "files.toml")
    raw_values = config_doc.get(field)
    if not isinstance(raw_values, list):
        violations.append(f"  linting/config/repo/files.toml: `{field}` must be a list of relative file paths")
        return []

    paths: list[Path] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            violations.append(f"  linting/config/repo/files.toml: `{field}` entries must be strings")
            continue
        paths.append(ROOT / raw_value)
    return paths


def main() -> int:
    violations: list[str] = []

    for required_file in _configured_paths("required_files", violations):
        if not required_file.exists():
            violations.append(f"  {rel(required_file)}: missing required config file")

    for requirement_file in _configured_paths("requirement_files", violations):
        if not requirement_file.exists():
            violations.append(f"  {rel(requirement_file)}: missing required requirements file")

    naming_policy = policy_section("naming")
    for raw_prefix in naming_policy.get("allowed_path_prefixes", []):
        if not isinstance(raw_prefix, str):
            violations.append("  linting/policy.toml: naming.allowed_path_prefixes entries must be strings")
            continue
        target = ROOT / raw_prefix
        if not target.exists():
            violations.append(f"  linting/policy.toml: allowlisted path does not exist: {raw_prefix}")

    return report("Lint config integrity violations", violations)


if __name__ == "__main__":
    sys.exit(main())
