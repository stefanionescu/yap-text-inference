"""Repo-local gitlint rules for Conventional Commit policy."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

from gitlint.options import ListOption
from gitlint.rules import LineRule, RuleViolation, CommitMessageTitle

_CONVENTIONAL_PATTERN = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<subject>.+)$")
_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "tooling" / "gitlint.toml"
_CONFIG_LABEL = "linting/config/tooling/gitlint.toml"


def _load_config() -> dict[str, object]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        loaded = tomllib.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _require_section(doc: dict[str, object], name: str) -> dict[str, object]:
    value = doc.get(name)
    if not isinstance(value, dict):
        raise RuntimeError(f"{_CONFIG_LABEL}: `{name}` must be a table")
    return value


def _require_string_list(doc: dict[str, object], name: str, label: str) -> list[str]:
    value = doc.get(name)
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise RuntimeError(f"{label}: `{name}` must be a list of strings")
    return [entry for entry in value if isinstance(entry, str)]


_TITLE_RULE = _require_section(_load_config(), "title_conventional_inference")
_TITLE_RULE_LABEL = f"{_CONFIG_LABEL} [title_conventional_inference]"
_ALLOWED_TYPES = _require_string_list(_TITLE_RULE, "allowed_types", _TITLE_RULE_LABEL)
_ALLOWED_SCOPES = _require_string_list(_TITLE_RULE, "allowed_scopes", _TITLE_RULE_LABEL)


class TitleConventionalInference(LineRule):
    """Enforce the repository's Conventional Commit title policy."""

    name = "title-conventional-inference"
    id = "UC1"
    target = CommitMessageTitle
    options_spec = [
        ListOption(
            "allowed-types",
            _ALLOWED_TYPES,
            "Comma-separated list of allowed commit types.",
        ),
        ListOption(
            "allowed-scopes",
            _ALLOWED_SCOPES,
            "Comma-separated list of allowed commit scopes.",
        ),
    ]

    def validate(self, line: str, _commit) -> list[RuleViolation] | None:
        match = _CONVENTIONAL_PATTERN.match(line)
        if not match:
            return [
                RuleViolation(
                    self.id,
                    "Title must match type(scope): subject Conventional Commit format",
                    line,
                )
            ]

        violations: list[RuleViolation] = []
        allowed_types = set(self.options["allowed-types"].value)
        allowed_scopes = set(self.options["allowed-scopes"].value)
        commit_type = match.group("type")
        scope = match.group("scope")
        subject = match.group("subject")

        if commit_type not in allowed_types:
            violations.append(
                RuleViolation(
                    self.id,
                    f"Title type must be one of: {', '.join(sorted(allowed_types))}",
                    line,
                )
            )

        if not scope:
            violations.append(RuleViolation(self.id, "Title scope is required", line))
        elif scope not in allowed_scopes:
            violations.append(
                RuleViolation(
                    self.id,
                    f"Title scope must be one of: {', '.join(sorted(allowed_scopes))}",
                    line,
                )
            )

        if subject != subject.lower():
            violations.append(RuleViolation(self.id, "Title subject must be lower-case", line))

        return violations or None
