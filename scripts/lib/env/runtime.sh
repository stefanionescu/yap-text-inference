#!/usr/bin/env bash

# Common repo-level runtime helpers for shell scripts.

# Initialize run/log directories under the repo root and ensure they exist.
# Usage: runtime_init_repo_paths "${ROOT_DIR}"
runtime_init_repo_paths() {
  local root_dir="${1:-}"
  local log_dir_default
  local run_dir_default

  if [ -z "${root_dir}" ]; then
    echo "runtime_init_repo_paths: root_dir is required" >&2
    return 1
  fi

  log_dir_default="${root_dir}/logs"
  run_dir_default="${root_dir}/.run"

  export LOG_DIR="${LOG_DIR:-${log_dir_default}}"
  export RUN_DIR="${RUN_DIR:-${run_dir_default}}"

  mkdir -p "${LOG_DIR}" "${RUN_DIR}"
}

