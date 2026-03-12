#!/usr/bin/env bash
# Shared helpers for repo-managed linting tool wrappers.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_CONFIG_DIR="${REPO_ROOT}/linting/config/tooling"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_CACHE_RELATIVE_DIR=".cache/tooling"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_INSTALL_SCRIPT="linting/tooling/install.sh"
# shellcheck disable=SC2034  # lint:justify -- reason: sourced tool resolver consumes this adapter variable -- ticket: N/A
TOOL_ERROR_CONTEXT="linting tool"
# shellcheck source=../lib/tool-resolver.sh
source "${REPO_ROOT}/linting/lib/tool-resolver.sh"

# source_tooling_config - Load a repo-local linting-tool config file by name.
source_tooling_config() {
  source_repo_tool_config "$1"
}

source_tooling_config "common"
source_tooling_config "tool-versions"
