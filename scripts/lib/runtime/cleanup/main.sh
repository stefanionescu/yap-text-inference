#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Runtime Cleanup Utilities
# =============================================================================
# Canonical cleanup module entrypoint.

_CLEANUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_CLEANUP_DIR}/../../noise/python.sh"
source "${_CLEANUP_DIR}/../../common/log.sh"
source "${_CLEANUP_DIR}/../../deps/venv/main.sh"
source "${_CLEANUP_DIR}/../../../config/values/runtime.sh"

# Remove directories silently.
# Usage: _cleanup_remove_dirs <dir1> [dir2] ...
_cleanup_remove_dirs() {
  local dir
  for dir in "$@"; do
    [ -z "${dir}" ] && continue
    if [ -e "${dir}" ]; then
      rm -rf "${dir}"
    fi
  done
}

source "${_CLEANUP_DIR}/caches.sh"
source "${_CLEANUP_DIR}/process.sh"
source "${_CLEANUP_DIR}/venv.sh"
source "${_CLEANUP_DIR}/tmp.sh"
