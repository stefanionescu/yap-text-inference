#!/usr/bin/env bash
# Shared Docker container entrypoint flow.
#
# Keeps stack main.sh scripts thin while preserving stack-specific usage text.
# Supports:
# - script mode: exec stack-specific start script
# - direct_common mode: launch common server path directly (no stack wrapper)

run_docker_main() {
  local stack="$1"
  local stack_script_dir="$2"
  local usage_fn="$3"
  local start_mode="${4:-script}"
  shift 4

  local start_target="${stack_script_dir}/start_server.sh"
  if [[ ${start_mode} == "script" ]] && [[ ${1:-} != "--" ]] && [[ -n ${1:-} ]]; then
    start_target="$1"
    shift
  fi

  if [[ ${1:-} == "--" ]]; then
    shift
  fi

  if [[ ${1:-} == "--help" ]] || [[ ${1:-} == "-h" ]]; then
    if declare -F "${usage_fn}" >/dev/null 2>&1; then
      "${usage_fn}"
    fi
    return 0
  fi

  local bootstrap_script="${stack_script_dir}/bootstrap.sh"

  if [ ! -f "${bootstrap_script}" ]; then
    log_err "[${stack}] ✗ bootstrap.sh not found at ${bootstrap_script}"
    exit 1
  fi
  # shellcheck disable=SC1090
  source "${bootstrap_script}"

  if [ -z "${TEXT_API_KEY:-}" ]; then
    log_err "[main] ✗ TEXT_API_KEY is required"
    exit 1
  fi

  case "${start_mode}" in
    direct_common)
      cd /app || exit 1
      local root_dir="${ROOT_DIR:-/app}"
      source "/app/common/scripts/server.sh"
      start_server_with_warmup "${stack}" "/app/common/scripts/warmup.sh" "${root_dir}"
      ;;
    script)
      if [ ! -x "${start_target}" ]; then
        log_err "[server] ✗ start_server.sh not found at ${start_target}"
        ls -la "${stack_script_dir}" || true
        exit 1
      fi
      exec "${start_target}"
      ;;
    *)
      log_err "[${stack}] ✗ invalid start mode: ${start_mode}"
      exit 1
      ;;
  esac
}
