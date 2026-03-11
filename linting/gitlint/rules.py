"""Repo-local gitlint rules for Conventional Commit policy."""

from __future__ import annotations

import re
from gitlint.options import ListOption
from gitlint.rules import LineRule, RuleViolation, CommitMessageTitle

_CONVENTIONAL_PATTERN = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<subject>.+)$")


class TitleConventionalInference(LineRule):
    """Enforce the repository's Conventional Commit title policy."""

    name = "title-conventional-inference"
    id = "UC1"
    target = CommitMessageTitle
    options_spec = [
        ListOption(
            "allowed-types",
            [
                "build",
                "chore",
                "ci",
                "docs",
                "feat",
                "fix",
                "perf",
                "refactor",
                "revert",
                "style",
                "test",
            ],
            "Comma-separated list of allowed commit types.",
        ),
        ListOption(
            "allowed-scopes",
            [
                "core",
                "config",
                "handlers",
                "messages",
                "tokens",
                "engines",
                "quantization",
                "docker",
                "scripts",
                "tests",
                "lint",
                "hooks",
                "docs",
                "deps",
                "rules",
            ],
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
