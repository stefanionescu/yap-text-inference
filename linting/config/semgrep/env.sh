#!/usr/bin/env bash

# lint:justify -- reason: configuration file sourced by the Semgrep wrapper -- ticket: N/A
# shellcheck disable=SC2034

SEMGREP_IMAGE="semgrep/semgrep:${SEMGREP_VERSION}"
SEMGREP_FLAGS=(
  --error
  --no-rewrite-rule-ids
  --metrics=off
  --disable-version-check
)
SEMGREP_TARGETS=("src" "tests" "scripts" "docker" "linting")
SEMGREP_EXCLUDES=("node_modules" ".venv" ".git")
SEMGREP_REGISTRY_RULESETS=("p/default" "p/python")
SEMGREP_LOCAL_RULE_FILES=("linting/config/semgrep/rules.yml")
