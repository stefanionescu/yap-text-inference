#!/usr/bin/env python
"""Validate repo-local lint/security configuration references."""

from __future__ import annotations

import sys
import json
from pathlib import Path
from linting.repo import ROOT, rel, report, string_list, policy_section, load_config_doc

POLICY_LABEL = "linting/config/repo/policy.toml"
PACKAGE_JSON = ROOT / "package.json"
HOOK_SETUP_PATH = ROOT / ".githooks" / "lib" / "setup.sh"
WHITELIZARD_PATH = ROOT / ".whitelizard"
REFERENCE_TARGETS = (
    ROOT / "README.md",
    ROOT / "ADVANCED.md",
    *sorted((ROOT / "rules").glob("*.md")),
)
SHELL_REFERENCE_TARGETS = {
    "scripts/lint.sh": ROOT / "scripts" / "lint.sh",
    "scripts/security.sh": ROOT / "scripts" / "security.sh",
}


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


def _package_scripts() -> set[str]:
    if not PACKAGE_JSON.exists():
        return set()

    try:
        raw_package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return set()

    raw_scripts = raw_package.get("scripts")
    if not isinstance(raw_scripts, dict):
        return set()

    return {name for name, value in raw_scripts.items() if isinstance(name, str) and isinstance(value, str)}


def _validate_shell_references(violations: list[str]) -> None:
    for doc_path in REFERENCE_TARGETS:
        try:
            content = doc_path.read_text(encoding="utf-8")
        except OSError as exc:
            violations.append(f"  {rel(doc_path)}: unable to read file: {exc}")
            continue

        for command_reference, target_path in SHELL_REFERENCE_TARGETS.items():
            if command_reference in content and not target_path.exists():
                violations.append(
                    f"  {rel(doc_path)}: references `{command_reference}`, but {rel(target_path)} does not exist",
                )


def _validate_hook_setup_scripts(violations: list[str]) -> None:
    if not HOOK_SETUP_PATH.exists():
        return

    try:
        content = HOOK_SETUP_PATH.read_text(encoding="utf-8")
    except Exception:
        return

    package_scripts = _package_scripts()
    for line in content.splitlines():
        marker = "bun run "
        if marker not in line:
            continue

        script_name = line.split(marker, maxsplit=1)[1].split()[0].strip('"')
        if script_name not in package_scripts:
            violations.append(
                f"  {rel(HOOK_SETUP_PATH)}: references `bun run {script_name}`, "
                f"but package.json has no `{script_name}` script",
            )


def _validate_lizard_allowlist(violations: list[str]) -> None:
    if not WHITELIZARD_PATH.exists():
        return

    try:
        lines = WHITELIZARD_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return

    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        relative_path = line.split(":", maxsplit=1)[0]
        candidate = ROOT / relative_path
        if not candidate.exists():
            violations.append(
                f"  {rel(WHITELIZARD_PATH)}:{index}: allowlisted path does not exist: {relative_path}",
            )


def main() -> int:
    violations: list[str] = []

    for requirement_file in _configured_paths("requirement_files", violations):
        if not requirement_file.exists():
            violations.append(f"  {rel(requirement_file)}: missing required requirements file")

    naming_policy = policy_section("naming")
    raw_prefixes = naming_policy.get("allowed_path_prefixes")
    if raw_prefixes is not None and not isinstance(raw_prefixes, list):
        violations.append(f"  {POLICY_LABEL}: naming.allowed_path_prefixes must be a list")
    for raw_prefix in string_list(raw_prefixes):
        target = ROOT / raw_prefix
        if not target.exists():
            violations.append(f"  {POLICY_LABEL}: allowlisted path does not exist: {raw_prefix}")

    _validate_shell_references(violations)
    _validate_hook_setup_scripts(violations)
    _validate_lizard_allowlist(violations)

    return report("Lint config integrity violations", violations)


if __name__ == "__main__":
    sys.exit(main())
