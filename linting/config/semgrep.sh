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
SEMGREP_TARGETS=("src" "scripts" "docker" "linting" ".githooks")
SEMGREP_EXCLUDES=("node_modules" ".venv" ".git" "tests/support/messages" "tests/support/prompts")
SEMGREP_REGISTRY_RULESETS=("p/default" "p/python")
SEMGREP_LOCAL_RULE_FILES=("linting/semgrep/rules.yml")
