#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Warmup Configuration
# =============================================================================
# Configuration defaults for warmup and benchmark scripts including
# timeouts, retry counts, and polling intervals.

_WARMUP_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_WARMUP_ENV_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/values/runtime.sh
source "${_WARMUP_ENV_DIR}/../../config/values/runtime.sh"

normalize_positive_int() {
  local var_name="${1:-}"
  local default_val="${2:-1}"
  local current_val

  if [ -z "${var_name}" ]; then
    echo "normalize_positive_int: var_name is required" >&2
    return 1
  fi

  current_val="${!var_name:-}"
  if [ -z "${current_val}" ]; then
    current_val="${default_val}"
  fi

  if ! [[ ${current_val} =~ ^[0-9]+$ ]] || ((current_val < 1)); then
    current_val="${default_val}"
  fi

  printf -v "${var_name}" '%s' "${current_val}"
  export "${var_name?}"
}

init_warmup_defaults() {
  local root_dir="${1:-}"
  local script_dir="${2:-}"

  if [ -z "${root_dir}" ] || [ -z "${script_dir}" ]; then
    echo "init_warmup_defaults: root_dir and script_dir are required" >&2
    return 1
  fi

  export WARMUP_HEALTH_POLL_INTERVAL_SECS="${WARMUP_HEALTH_POLL_INTERVAL_SECS:-${CFG_WARMUP_HEALTH_POLL_INTERVAL_SECS_DEFAULT}}"
  export WARMUP_RUN_DELAY_SECS="${WARMUP_RUN_DELAY_SECS:-${CFG_WARMUP_RUN_DELAY_SECS_DEFAULT}}"
  export WARMUP_DEFAULT_CONN_FALLBACK="${WARMUP_DEFAULT_CONN_FALLBACK:-${CFG_WARMUP_DEFAULT_CONN_FALLBACK}}"

  export WARMUP_LOG_FILE="${WARMUP_LOG_FILE:-${root_dir}/${CFG_RUNTIME_WARMUP_LOG_FILE}}"
  export WARMUP_LOCK_FILE="${WARMUP_LOCK_FILE:-${root_dir}/${CFG_RUNTIME_WARMUP_LOCK_FILE}}"
  export WARMUP_HEALTH_CHECK_SCRIPT="${WARMUP_HEALTH_CHECK_SCRIPT:-${script_dir}/lib/common/health.sh}"

  normalize_positive_int WARMUP_TIMEOUT_SECS "${CFG_WARMUP_TIMEOUT_SECS_DEFAULT}"
  normalize_positive_int WARMUP_RETRIES "${CFG_WARMUP_RETRIES_DEFAULT}"
}
