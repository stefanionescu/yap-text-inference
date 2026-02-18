#!/usr/bin/env bash
# =============================================================================
# Warmup Test Runner Utilities
# =============================================================================
# Provides reusable functions for running warmup and benchmark tests with
# retries, logging, and persona variant handling.

_WARMUP_RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_WARMUP_RUNNER_DIR}/../../config/values/core.sh"

# =============================================================================
# PERSONA VARIANT HANDLING
# =============================================================================

# Add a persona variant to the global array.
# Usage: warmup_add_persona_variant <gender> [personality]
warmup_add_persona_variant() {
  local gender
  local personality
  gender="$(str_trim "${1:-}")"
  personality="$(str_trim "${2:-}")"
  if [ -z "${gender}" ]; then
    return
  fi
  WARMUP_PERSONA_VARIANTS+=("${gender}|${personality}")
}

# Parse a comma-separated persona spec string.
# Format: "female,male:sarcastic,neutral:friendly"
# Usage: warmup_parse_persona_spec <spec>
warmup_parse_persona_spec() {
  local spec="${1:-}"
  local entries
  IFS=',' read -r -a entries <<<"${spec}"
  local entry
  for entry in "${entries[@]}"; do
    entry="$(str_trim "${entry}")"
    if [ -z "${entry}" ]; then
      continue
    fi
    if [[ ${entry} == *:* ]]; then
      warmup_add_persona_variant "${entry%%:*}" "${entry#*:}"
    else
      warmup_add_persona_variant "${entry}" ""
    fi
  done
}

# Build persona variants from env overrides or repo defaults.
# Populates the global WARMUP_PERSONA_VARIANTS array.
# Usage: warmup_detect_persona_variants <py_bin>
warmup_detect_persona_variants() {
  local py_bin="${1:-python}"
  WARMUP_PERSONA_VARIANTS=()

  if [ -n "${WARMUP_PERSONAS:-}" ]; then
    warmup_parse_persona_spec "${WARMUP_PERSONAS}"
    return
  fi

  if [ -n "${GENDER:-}" ]; then
    warmup_add_persona_variant "${GENDER}" "${PERSONALITY:-}"
    return
  fi

  local py_output=""
  if py_output="$("${py_bin}" -m src.scripts.warmup list 2>/dev/null)"; then
    while IFS= read -r line; do
      line="$(str_trim "${line}")"
      if [ -z "${line}" ]; then
        continue
      fi
      if [[ ${line} == *:* ]]; then
        warmup_add_persona_variant "${line%%:*}" "${line#*:}"
      else
        warmup_add_persona_variant "${line}" ""
      fi
    done <<<"${py_output}"
  fi

  if [ "${#WARMUP_PERSONA_VARIANTS[@]}" -eq 0 ]; then
    warmup_add_persona_variant "female" ""
    warmup_add_persona_variant "male" ""
  fi
}

# =============================================================================
# LABEL UTILITIES
# =============================================================================

# Sanitize a string for use in log file names.
# Converts to lowercase and replaces non-alphanumeric chars with underscores.
warmup_sanitize_label() {
  local value="${1:-}"
  value="${value,,}"
  value="${value//[^a-z0-9]/_}"
  echo "${value}"
}

# Generate a safe log prefix from a raw label.
warmup_safe_log_prefix() {
  local raw="${1:-run}"
  local cleaned
  cleaned="$(warmup_sanitize_label "${raw}")"
  if [ -z "${cleaned}" ]; then
    cleaned="run"
  fi
  echo "${cleaned}"
}

# =============================================================================
# TEST EXECUTION
# =============================================================================

# Execute a warmup/bench python helper and tee stdout/stderr into a log file.
# Usage: warmup_run_py_tool <log_path> <py_bin> <args...>
warmup_run_py_tool() {
  local log_path="$1"
  local py_bin="$2"
  shift 2
  if "${py_bin}" "$@" >"${log_path}" 2>&1; then
    return 0
  fi
  return 1
}

# Execute a python helper with retries, logging only the final status.
# Usage: warmup_run_with_retries <label> <log_prefix> <py_bin> <log_dir> <retries> <cmd...>
warmup_run_with_retries() {
  local label="${1:-}"
  local log_prefix="${2:-run}"
  local py_bin="${3:-python}"
  local log_dir="${4:-./logs}"
  local retries="${5:-1}"
  shift 5
  local -a cmd=("$@")
  local attempt=1
  local run_log=""
  local last_log=""

  for ((attempt = 1; attempt <= retries; attempt++)); do
    run_log="${log_dir}/${log_prefix}_attempt${attempt}.log"
    last_log="${run_log}"
    warmup_log_internal "${label}: attempt ${attempt} → ${run_log}"
    if warmup_run_py_tool "${run_log}" "${py_bin}" "${cmd[@]}"; then
      warmup_log_phase_result "${label}" "OK"
      return 0
    fi
    warmup_log_internal "${label}: attempt ${attempt} failed (see ${run_log})"
  done

  warmup_log_phase_result "${label}" "FAIL" "${last_log}"
  return 1
}

# =============================================================================
# LOGGING HELPERS
# =============================================================================

# Internal warmup log (to file only).
warmup_log_internal() {
  echo "[warmup] $*" >>"${WARMUP_LOG_FILE:-/dev/null}"
}

# Log phase results to both stderr (terminal) and server.log for visibility.
warmup_log_phase_result() {
  local label="${1:-}"
  local status="${2:-}"
  local log_path="${3:-}"
  local line=""
  if [ "${status}" = "OK" ]; then
    line="[warmup] ${label} (OK)"
  else
    if [ -n "${log_path}" ]; then
      line="[warmup] ${label} (FAIL) (see ${log_path})"
    else
      line="[warmup] ${label} (FAIL)"
    fi
  fi
  # Log to stderr via log_info (if available) and append to server.log
  if type log_info >/dev/null 2>&1; then
    log_info "${line}"
  else
    echo "${line}" >&2
  fi
  local server_log="${ROOT_DIR:-}/server.log"
  if [ -n "${ROOT_DIR:-}" ]; then
    echo "${line}" >>"${server_log}"
  fi
}

# =============================================================================
# PYTHON INTERPRETER DETECTION
# =============================================================================

# Find the best available Python interpreter.
# Priority: venv python > engine-specific python > python3 > python
warmup_choose_python() {
  # Try venv python first
  if command -v get_venv_python >/dev/null 2>&1; then
    local venv_py
    venv_py="$(get_venv_python 2>/dev/null || true)"
    if [ -n "${venv_py}" ] && [ -x "${venv_py}" ]; then
      echo "${venv_py}"
      return 0
    fi
  elif command -v get_venv_dir >/dev/null 2>&1; then
    local fallback_dir
    fallback_dir="$(get_venv_dir)"
    local venv_py="${fallback_dir}/bin/python"
    if [ -x "${venv_py}" ]; then
      echo "${venv_py}"
      return 0
    fi
  fi

  # Try engine-specific python
  if command -v get_python_binary_for_engine >/dev/null 2>&1; then
    local engine_py
    engine_py="$(get_python_binary_for_engine 2>/dev/null || true)"
    if [ -n "${engine_py}" ] && command -v "${engine_py}" >/dev/null 2>&1; then
      command -v "${engine_py}"
      return 0
    fi
  fi

  # Fall back to system python
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

# =============================================================================
# DEPLOY MODE DETECTION
# =============================================================================

# Infer which prompt template to use so warmup exercises the deployed subset.
warmup_detect_prompt_mode() {
  local deploy_mode="${DEPLOY_MODE:-}"
  case "${deploy_mode}" in
    chat)
      echo "chat"
      return 0
      ;;
    tool)
      echo "tool"
      return 0
      ;;
  esac

  local chat_flag="${DEPLOY_CHAT:-}"
  local tool_flag="${DEPLOY_TOOL:-}"
  if [[ ${chat_flag} == "1" && ${tool_flag} == "1" ]]; then
    echo "both"
  elif [[ ${chat_flag} == "1" ]]; then
    echo "chat"
  elif [[ ${tool_flag} == "1" ]]; then
    echo "tool"
  else
    echo "both"
  fi
}

# =============================================================================
# MAX CONNECTIONS DETECTION
# =============================================================================

# Detect the maximum connection count from env overrides or config fallback.
# Usage: warmup_detect_max_conn <py_bin> <root_dir> <default_fallback>
warmup_detect_max_conn() {
  local py_bin="${1:-python}"
  local root_dir="${2:-.}"
  local default_fallback="${3:-${CFG_WARMUP_DEFAULT_CONN_FALLBACK}}"

  if [[ -n ${MAX_CONCURRENT_CONNECTIONS:-} ]]; then
    echo "${MAX_CONCURRENT_CONNECTIONS}"
    return 0
  fi

  local py_output
  if py_output="$("${py_bin}" -c "
import sys
import os
sys.path.insert(0, '${root_dir}')
from src.config.limits import MAX_CONCURRENT_CONNECTIONS
print(MAX_CONCURRENT_CONNECTIONS)
" 2>/dev/null)"; then
    if [[ -n ${py_output} && ${py_output} =~ ^[0-9]+$ ]]; then
      echo "${py_output}"
      return 0
    fi
  fi

  echo "${default_fallback}"
  return 1
}
