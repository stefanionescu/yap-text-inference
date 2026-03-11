#!/usr/bin/env bash
# Project shell hook for staged shell linting on commit and full shell linting on push.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook dispatch helper -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/dispatch.sh"
run_project_stage shell "$@"
