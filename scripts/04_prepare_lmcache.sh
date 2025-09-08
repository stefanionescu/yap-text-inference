#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Configuring LMCache local backend"

export USE_LMCACHE=${USE_LMCACHE:-1}
export LMCACHE_USE_EXPERIMENTAL=${LMCACHE_USE_EXPERIMENTAL:-True}
export LMCACHE_CONFIG_FILE=${LMCACHE_CONFIG_FILE:-${ROOT_DIR}/lmcache.yaml}

# Ensure repo-local LMCache store
STORE_DIR="${ROOT_DIR}/.lmcache_store"
mkdir -p "${STORE_DIR}" || true

# Write/update config file to point to repo-local store
cat >"${LMCACHE_CONFIG_FILE}" <<YAML
chunk_size: 256
local_cpu: true
max_local_cpu_size: 6.0
local_disk: "file://${STORE_DIR}/"
max_local_disk_size: 20.0
YAML

# Legacy cleanup: remove any old /workspace copies to avoid confusion
[ -f "/workspace/lmcache.yaml" ] && rm -f /workspace/lmcache.yaml || true
[ -d "/workspace/lmcache_store" ] && rmdir /workspace/lmcache_store 2>/dev/null || true


