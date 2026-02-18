#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# TRT-LLM Installation Utilities
# =============================================================================
# Canonical TRT install module entrypoint.

_TRT_INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=./config.sh
source "${_TRT_INSTALL_DIR}/config.sh"
# shellcheck source=./python_deps.sh
source "${_TRT_INSTALL_DIR}/python_deps.sh"
# shellcheck source=./validate.sh
source "${_TRT_INSTALL_DIR}/validate.sh"
# shellcheck source=./repo.sh
source "${_TRT_INSTALL_DIR}/repo.sh"

# Suppress git trace logging for both direct git and pip internal git operations.
unset GIT_TRACE GIT_CURL_VERBOSE GIT_TRACE_CURL GIT_TRACE_PACKET GIT_TRACE_PERFORMANCE GIT_TRACE_SETUP
export GIT_CURL_VERBOSE=0 GIT_TRACE=0 GIT_TRACE_CURL=0
