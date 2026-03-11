#!/usr/bin/env bash
# Project quality hook for complexity and dependency hygiene checks.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook dispatch helper -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/dispatch.sh"
run_project_stage quality "$@"
