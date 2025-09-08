#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Configuring LMCache local backend"

export USE_LMCACHE=${USE_LMCACHE:-1}
export LMCACHE_USE_EXPERIMENTAL=${LMCACHE_USE_EXPERIMENTAL:-True}
export LMCACHE_CONFIG_FILE=${LMCACHE_CONFIG_FILE:-/workspace/lmcache.yaml}

if [ ! -f "$LMCACHE_CONFIG_FILE" ]; then
  log_warn "LMCache config not found at $LMCACHE_CONFIG_FILE; copying default from repo"
  mkdir -p "/workspace"
  cp -f "${ROOT_DIR}/lmcache.yaml" "/workspace/lmcache.yaml" || true
fi

mkdir -p /workspace/lmcache_store || true


