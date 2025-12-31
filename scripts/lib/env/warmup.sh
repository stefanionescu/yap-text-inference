#!/usr/bin/env bash

# Warmup/bench-specific configuration shared across scripts.

warmup_normalize_positive_int() {
  local var_name="${1:-}"
  local default_val="${2:-1}"
  local current_val

  if [ -z "${var_name}" ]; then
    echo "warmup_normalize_positive_int: var_name is required" >&2
    return 1
  fi

  current_val="${!var_name:-}"
  if [ -z "${current_val}" ]; then
    current_val="${default_val}"
  fi

  if ! [[ "${current_val}" =~ ^[0-9]+$ ]] || (( current_val < 1 )); then
    current_val="${default_val}"
  fi

  printf -v "${var_name}" '%s' "${current_val}"
  export "${var_name?}"
}

warmup_init_defaults() {
  local root_dir="${1:-}"
  local script_dir="${2:-}"
  local log_dir
  local run_dir

  if [ -z "${root_dir}" ] || [ -z "${script_dir}" ]; then
    echo "warmup_init_defaults: root_dir and script_dir are required" >&2
    return 1
  fi

  log_dir="${LOG_DIR:-${root_dir}/logs}"
  run_dir="${RUN_DIR:-${root_dir}/.run}"

  export WARMUP_HEALTH_POLL_INTERVAL_SECS="${WARMUP_HEALTH_POLL_INTERVAL_SECS:-2}"
  export WARMUP_RUN_DELAY_SECS="${WARMUP_RUN_DELAY_SECS:-1}"
  export WARMUP_DEFAULT_CONN_FALLBACK="${WARMUP_DEFAULT_CONN_FALLBACK:-8}"

  export WARMUP_LOG_FILE="${WARMUP_LOG_FILE:-${log_dir}/warmup.log}"
  export WARMUP_LOCK_FILE="${WARMUP_LOCK_FILE:-${run_dir}/warmup.lock}"
  export WARMUP_HEALTH_CHECK_SCRIPT="${WARMUP_HEALTH_CHECK_SCRIPT:-${script_dir}/lib/common/health.sh}"

  warmup_normalize_positive_int WARMUP_TIMEOUT_SECS 300
  warmup_normalize_positive_int WARMUP_RETRIES 1
}
