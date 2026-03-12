#!/usr/bin/env python
"""Validate repo-local lint/security configuration references."""

from __future__ import annotations

import sys
import json
from pathlib import Path
from linting.repo import ROOT, HOOKS_DIR, rel, report, string_list, policy_section, load_config_doc

POLICY_LABEL = "linting/config/repo/policy.toml"
FILES_LABEL = "linting/config/repo/files.toml"
PYMARKDOWN_LABEL = "linting/config/rules/pymarkdown.toml"
GITLINT_LABEL = "linting/config/tooling/gitlint.toml"
PACKAGE_JSON = ROOT / "package.json"
HOOK_SETUP_PATH = HOOKS_DIR / "lib" / "setup.sh"
WHITELIZARD_PATH = ROOT / ".whitelizard"
_REPO_FILES = load_config_doc("repo", "files.toml")
_PYMARKDOWN_RULES = load_config_doc("rules", "pymarkdown.toml")
_GITLINT_RULES = load_config_doc("tooling", "gitlint.toml")


def _configured_paths(
    config_doc: dict[str, object],
    field: str,
    config_label: str,
    violations: list[str],
) -> list[Path]:
    raw_values = config_doc.get(field)
    if not isinstance(raw_values, list):
        violations.append(f"  {config_label}: `{field}` must be a list of relative file paths")
        return []

    paths: list[Path] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            violations.append(f"  {config_label}: `{field}` entries must be strings")
            continue
        paths.append(ROOT / raw_value)
    return paths


def _configured_patterns(
    config_doc: dict[str, object],
    field: str,
    config_label: str,
    violations: list[str],
) -> list[str]:
    raw_values = config_doc.get(field)
    if not isinstance(raw_values, list):
        violations.append(f"  {config_label}: `{field}` must be a list of glob patterns")
        return []
    patterns: list[str] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            violations.append(f"  {config_label}: `{field}` entries must be strings")
            continue
        patterns.append(raw_value)
    return patterns


def _configured_string_mapping(
    config_doc: dict[str, object],
    field: str,
    config_label: str,
    violations: list[str],
) -> dict[str, Path]:
    raw_values = config_doc.get(field)
    if not isinstance(raw_values, dict):
        violations.append(f"  {config_label}: `{field}` must be a table of string values")
        return {}

    resolved: dict[str, Path] = {}
    for key, value in raw_values.items():
        if not isinstance(key, str) or not isinstance(value, str):
            violations.append(f"  {config_label}: `{field}` entries must map strings to strings")
            continue
        resolved[key] = ROOT / value
    return resolved


def _reference_targets(violations: list[str]) -> list[Path]:
    targets = _configured_paths(_REPO_FILES, "reference_docs", FILES_LABEL, violations)
    for pattern in _configured_patterns(_REPO_FILES, "reference_doc_globs", FILES_LABEL, violations):
        targets.extend(sorted(ROOT.glob(pattern)))
    unique_targets = {path.resolve(): path for path in targets}
    return [unique_targets[key] for key in sorted(unique_targets)]


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
    shell_reference_targets = _configured_string_mapping(
        _REPO_FILES,
        "shell_reference_targets",
        FILES_LABEL,
        violations,
    )
    for doc_path in _reference_targets(violations):
        try:
            content = doc_path.read_text(encoding="utf-8")
        except OSError as exc:
            violations.append(f"  {rel(doc_path)}: unable to read file: {exc}")
            continue

        for command_reference, target_path in shell_reference_targets.items():
            if command_reference in content and not target_path.exists():
                violations.append(
                    f"  {rel(doc_path)}: references `{command_reference}`, but {rel(target_path)} does not exist",
                )


def _validate_pymarkdown_config(violations: list[str]) -> None:
    run_rules = _PYMARKDOWN_RULES.get("run")
    if not isinstance(run_rules, dict):
        violations.append(f"  {PYMARKDOWN_LABEL}: `run` must be a table")
        return

    plugin_files = _configured_paths(run_rules, "plugin_files", f"{PYMARKDOWN_LABEL} [run]", violations)
    enabled_rules = run_rules.get("enabled_rules")
    if not isinstance(enabled_rules, list) or any(not isinstance(value, str) for value in enabled_rules):
        violations.append(f"  {PYMARKDOWN_LABEL} [run]: `enabled_rules` must be a list of strings")

    for plugin_file in plugin_files:
        if not plugin_file.exists():
            violations.append(f"  {rel(plugin_file)}: missing PyMarkdown plugin configured in {PYMARKDOWN_LABEL}")


def _validate_gitlint_config(violations: list[str]) -> None:
    title_rule = _GITLINT_RULES.get("title_conventional_inference")
    if not isinstance(title_rule, dict):
        violations.append(f"  {GITLINT_LABEL}: `title_conventional_inference` must be a table")
        return

    for field in ("allowed_types", "allowed_scopes"):
        values = title_rule.get(field)
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            violations.append(f"  {GITLINT_LABEL} [title_conventional_inference]: `{field}` must be a list of strings")


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

    for requirement_file in _configured_paths(_REPO_FILES, "requirement_files", FILES_LABEL, violations):
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
    _validate_pymarkdown_config(violations)
    _validate_gitlint_config(violations)

    return report("Lint config integrity violations", violations)


if __name__ == "__main__":
    sys.exit(main())
