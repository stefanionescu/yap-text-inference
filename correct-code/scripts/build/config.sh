#!/usr/bin/env bash

# Shared helpers for persisting and diffing build configuration.

# Keys that meaningfully impact quantization and engine builds.
ORPHEUS_BUILD_CONFIG_KEYS=(
  MODEL_ID
  MODEL_PRESET
  ORPHEUS_PRECISION_MODE
  CHECKPOINT_DIR
  TRTLLM_ENGINE_DIR
  TRTLLM_REPO_DIR
  TRTLLM_DTYPE
  TRTLLM_MAX_INPUT_LEN
  TRTLLM_MAX_OUTPUT_LEN
  TRTLLM_MAX_BATCH_SIZE
  AWQ_BLOCK_SIZE
  CALIB_SIZE
  KV_FREE_GPU_FRAC
  KV_ENABLE_BLOCK_REUSE
  HF_DEPLOY_REPO_ID
  HF_DEPLOY_USE
  HF_DEPLOY_ENGINE_LABEL
  HF_DEPLOY_SKIP_BUILD_IF_ENGINES
  HF_DEPLOY_STRICT_ENV_MATCH
  HF_DEPLOY_WORKDIR
  HF_DEPLOY_VALIDATE
)

_orpheus_locate_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  return 1
}

orpheus_build_config_dump() {
  local key
  for key in "${ORPHEUS_BUILD_CONFIG_KEYS[@]}"; do
    printf '%s=%s\n' "$key" "${!key:-}"
  done
}

orpheus_build_config_signature() {
  local py
  if ! py=$(_orpheus_locate_python); then
    echo "no-python"
    return 0
  fi
  local data
  data="$(orpheus_build_config_dump)"
  echo "$data" | "$py" -c '
import hashlib
import sys

payload = sys.stdin.read().encode("utf-8")
print(hashlib.sha256(payload).hexdigest())
'
}

orpheus_write_build_config() {
  local target="${1:-${ROOT_DIR:-.}/.run/build_config.env}"
  local signature
  signature="$(orpheus_build_config_signature)"
  mkdir -p "$(dirname "$target")"
  {
    echo "# Auto-generated build configuration - do not edit manually"
    local key
    for key in "${ORPHEUS_BUILD_CONFIG_KEYS[@]}"; do
      local value="${!key:-}"
      printf 'BUILD_%s=%q\n' "$key" "$value"
    done
    printf 'BUILD_SIGNATURE_SHA=%q\n' "$signature"
    printf 'BUILD_TIMESTAMP=%q\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$target"
}

orpheus_build_config_changed() {
  local config_file="$1"
  local log_prefix="${2:-[build-config]}"

  if [[ ! -f "$config_file" ]]; then
    echo "${log_prefix} No previous build config found - rebuild needed"
    return 0
  fi

  # shellcheck disable=SC1090
  source "$config_file" 2>/dev/null || return 0

  local changed=1
  local key
  for key in "${ORPHEUS_BUILD_CONFIG_KEYS[@]}"; do
    local current="${!key:-}"
    local saved_var="BUILD_${key}"
    local previous="${!saved_var:-}"
    if [[ "${current:-}" != "${previous:-}" ]]; then
      echo "${log_prefix} ${key} changed: '${previous:-}' -> '${current:-}'"
      changed=0
    fi
  done

  local signature
  signature="$(orpheus_build_config_signature)"
  if [[ "${BUILD_SIGNATURE_SHA:-}" != "${signature}" ]]; then
    changed=0
  fi
  return $changed
}

