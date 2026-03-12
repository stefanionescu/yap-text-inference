#!/usr/bin/env bash
# Shared helpers for repo-managed security wrappers.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_CONFIG_DIR="${REPO_ROOT}/linting/config/security"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_CACHE_RELATIVE_DIR=".cache/security"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_INSTALL_SCRIPT="linting/security/install.sh"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_ERROR_CONTEXT="security tool"
# shellcheck source=../lib/tool-resolver.sh
source "${REPO_ROOT}/linting/lib/tool-resolver.sh"

# source_security_config - Load a repo-local shell config file by name.
source_security_config() {
  source_repo_tool_config "$1"
}

source_security_config "common"
source_security_config "tool-versions"

# require_docker - Abort if Docker or the Docker daemon is unavailable.
require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is required" >&2
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "error: docker daemon unavailable" >&2
    exit 1
  fi
}
