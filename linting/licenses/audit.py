#!/usr/bin/env python
"""Audit licenses for repo dependency roots and their installed transitive dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from collections import deque
from importlib import metadata
from linting.repo import ROOT, rel, report, require_string, load_config_doc, require_section, require_string_list

_LICENSES_CONFIG = load_config_doc("licenses.toml")
_LICENSES_LABEL = "linting/config/licenses.toml"
_PARSING_RULES = require_section(_LICENSES_CONFIG, "parsing", _LICENSES_LABEL)
_PARSING_LABEL = f"{_LICENSES_LABEL} [parsing]"
_NORMALIZE_RE = re.compile(require_string(_PARSING_RULES, "normalize_pattern", _PARSING_LABEL))
_NAME_RE = re.compile(require_string(_PARSING_RULES, "name_pattern", _PARSING_LABEL))
_SKIP_PREFIXES = tuple(require_string_list(_PARSING_RULES, "skip_prefixes", _PARSING_LABEL))
_EDITABLE_PREFIXES = tuple(require_string_list(_PARSING_RULES, "editable_prefixes", _PARSING_LABEL))
_DIRECT_REFERENCE_SEPARATOR = require_string(_PARSING_RULES, "direct_reference_separator", _PARSING_LABEL)
_EGG_FRAGMENT = require_string(_PARSING_RULES, "egg_fragment", _PARSING_LABEL)
_UNKNOWN_LICENSES = {
    value.strip().lower() for value in require_string_list(_PARSING_RULES, "unknown_licenses", _PARSING_LABEL)
}
_LICENSE_FILE_NAMES = tuple(
    value.strip().lower() for value in require_string_list(_PARSING_RULES, "license_file_names", _PARSING_LABEL)
)


def _normalize_name(value: str) -> str:
    return _NORMALIZE_RE.sub("-", value).strip().lower()


def _parse_requirement_name(raw_value: str) -> str | None:
    value = raw_value.split("#", 1)[0].strip()
    if not value or value.startswith(_SKIP_PREFIXES):
        return None
    if value.startswith(_EDITABLE_PREFIXES):
        if _EGG_FRAGMENT in value:
            return _normalize_name(value.split(_EGG_FRAGMENT, 1)[1])
        return None
    if _DIRECT_REFERENCE_SEPARATOR in value:
        return _normalize_name(value.split(_DIRECT_REFERENCE_SEPARATOR, 1)[0])
    match = _NAME_RE.match(value)
    if match is None:
        return None
    return _normalize_name(match.group(1))


def _requirement_files() -> list[Path]:
    config_doc = load_config_doc("repo", "files.toml")
    return [
        ROOT / raw_value
        for raw_value in require_string_list(config_doc, "requirement_files", "linting/config/repo/files.toml")
    ]


def _root_packages() -> set[str]:
    roots: set[str] = set()
    for requirement_file in _requirement_files():
        if not requirement_file.exists():
            continue
        for raw_line in requirement_file.read_text(encoding="utf-8").splitlines():
            package_name = _parse_requirement_name(raw_line)
            if package_name:
                roots.add(package_name)
    return roots


def _installed_distributions() -> dict[str, metadata.Distribution]:
    installed: dict[str, metadata.Distribution] = {}
    for dist in metadata.distributions():
        dist_name = _metadata_value(dist, "Name")
        if dist_name:
            installed[_normalize_name(dist_name)] = dist
    return installed


def _dependency_names(
    dist: metadata.Distribution,
    installed: dict[str, metadata.Distribution],
    resolved: dict[str, metadata.Distribution],
) -> list[str]:
    names: list[str] = []
    for raw_requirement in dist.requires or []:
        dependency_name = _parse_requirement_name(raw_requirement)
        if dependency_name and dependency_name in installed and dependency_name not in resolved:
            names.append(dependency_name)
    return names


def _resolve_repo_distributions() -> list[metadata.Distribution]:
    installed = _installed_distributions()
    queue = deque(root for root in sorted(_root_packages()) if root in installed)
    resolved: dict[str, metadata.Distribution] = {}

    while queue:
        package_name = queue.popleft()
        if package_name in resolved:
            continue

        dist = installed.get(package_name)
        if dist is None:
            continue
        resolved[package_name] = dist

        for dependency_name in _dependency_names(dist, installed, resolved):
            queue.append(dependency_name)

    return [resolved[key] for key in sorted(resolved)]


def _first_known_license(values: list[str] | None) -> str | None:
    for raw_value in values or []:
        normalized = raw_value.strip()
        if normalized and normalized.lower() not in _UNKNOWN_LICENSES:
            return normalized
    return None


def _license_from_classifiers(classifier_values: list[str]) -> str | None:
    license_classifiers = []
    for classifier_value in classifier_values:
        if classifier_value.startswith("License :: "):
            license_classifiers.append(classifier_value.split(" :: ")[-1].strip())

    if not license_classifiers:
        return None
    unique = list(dict.fromkeys(license_classifiers))
    return " OR ".join(unique)


def _license_from_metadata(dist: metadata.Distribution) -> str:
    known = _first_known_license([_metadata_value(dist, "License-Expression")])
    if known:
        return known

    known = _first_known_license(dist.metadata.get_all("License"))
    if known:
        return known

    known = _license_from_classifiers(dist.metadata.get_all("Classifier") or [])
    if known:
        return known

    return _license_from_files(dist) or "UNKNOWN"


def _candidate_license_files(dist: metadata.Distribution) -> list[Path]:
    return [
        Path(str(dist.locate_file(rel_path)))
        for rel_path in dist.files or []
        if any(token in str(rel_path.name).lower() for token in _LICENSE_FILE_NAMES)
    ]


def _detect_license_from_text(normalized: str) -> str | None:
    if not normalized:
        return None
    known_checks = (
        (
            "permission is hereby granted, free of charge, to any person obtaining a copy",
            "MIT",
        ),
        ("gnu lesser general public license", "LGPL"),
        ("gnu general public license", "GPL"),
        ("permission to use, copy, modify, and/or distribute this software", "ISC"),
    )
    for token, label in known_checks:
        if token in normalized:
            return label
    if "apache license" in normalized and "version 2.0" in normalized:
        return "Apache-2.0"
    if "mozilla public license" in normalized and "version 2.0" in normalized:
        return "MPL-2.0"
    return _detect_bsd_license(normalized)


def _detect_bsd_license(normalized: str) -> str | None:
    if "redistribution and use in source and binary forms" not in normalized:
        return None
    if "without modification" not in normalized:
        return None
    if "neither the name" in normalized:
        return "BSD-3-Clause"
    return "BSD-2-Clause"


def _license_from_files(dist: metadata.Distribution) -> str | None:
    for path in _candidate_license_files(dist):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        detected = _detect_license_from_text(" ".join(content.lower().split()))
        if detected:
            return detected

    return None


def _config_strings(config_doc: dict[str, object], key: str) -> list[str]:
    return [value.strip() for value in require_string_list(config_doc, key, _LICENSES_LABEL) if value.strip()]


def _metadata_value(dist: metadata.Distribution, key: str) -> str:
    values = dist.metadata.get_all(key)
    if not values:
        return ""
    first = values[0]
    return first if isinstance(first, str) else ""


def _normalized_config_strings(config_doc: dict[str, object], key: str) -> set[str]:
    return {_normalize_name(value) for value in _config_strings(config_doc, key)}


def _string_mapping(config_doc: dict[str, object], key: str) -> dict[str, str]:
    raw_mapping = config_doc.get(key)
    if not isinstance(raw_mapping, dict):
        raise RuntimeError(f"{_LICENSES_LABEL}: `{key}` must be a table")
    return {
        _normalize_name(package_name): str(license_value).strip()
        for package_name, license_value in raw_mapping.items()
        if isinstance(package_name, str) and isinstance(license_value, str) and str(license_value).strip()
    }


def _load_policy() -> tuple[set[str], list[str], set[str], dict[str, str]]:
    config_doc = _LICENSES_CONFIG
    allowed_exact = set(_config_strings(config_doc, "allowed_exact"))
    allowed_substrings = [value.lower() for value in _config_strings(config_doc, "allowed_substrings")]
    ignored_packages = _normalized_config_strings(config_doc, "ignored_packages")
    overrides = _string_mapping(config_doc, "package_overrides")
    return allowed_exact, allowed_substrings, ignored_packages, overrides


def _is_allowed(license_value: str, allowed_exact: set[str], allowed_substrings: list[str]) -> bool:
    if license_value in allowed_exact:
        return True
    normalized = license_value.lower()
    return any(token in normalized for token in allowed_substrings)


def main() -> int:
    violations: list[str] = []
    allowed_exact, allowed_substrings, ignored_packages, package_overrides = _load_policy()

    for dist in _resolve_repo_distributions():
        dist_name = _metadata_value(dist, "Name")
        normalized_name = _normalize_name(dist_name)
        if not dist_name or normalized_name in ignored_packages:
            continue

        effective_license = package_overrides.get(normalized_name, _license_from_metadata(dist))
        if _is_allowed(effective_license, allowed_exact, allowed_substrings):
            continue

        violations.append(
            f"  {dist_name}=={dist.version}: unapproved license `{effective_license}` "
            f"(audited from repo requirements under {rel(ROOT / 'requirements-dev.txt')})"
        )

    return report("License audit violations", violations)


if __name__ == "__main__":
    sys.exit(main())
