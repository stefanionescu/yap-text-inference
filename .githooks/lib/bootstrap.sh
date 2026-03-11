#!/usr/bin/env bash
# Shared repo-tool bootstrap for git hook scripts.

set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(git rev-parse --show-toplevel)}"

# shellcheck disable=SC1091  # lint:justify -- reason: hooks source the shared repo lint bootstrap to resolve repo-managed tooling -- ticket: N/A
source "${ROOT_DIR}/linting/common.sh"
ensure_repo_python_env
