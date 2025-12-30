#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source venv helpers, logging, and env defaults
source "${SCRIPT_DIR}/lib/deps/venv.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/common/warnings.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/common/log.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/runtime.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/server.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/warmup.sh" 2>/dev/null || true

runtime_init_repo_paths "${ROOT_DIR}"
server_init_network_defaults
warmup_init_defaults "${ROOT_DIR}" "${SCRIPT_DIR}"

declare -a WARMUP_PERSONA_VARIANTS=()

log_warmup() {
  local line="[warmup] $*"
  echo "${line}" >> "${WARMUP_LOG_FILE}"
}

log_warmup_file() {
  local line="[warmup] $*"
  echo "${line}" >> "${WARMUP_LOG_FILE}"
}

# Log phase results to both stderr (terminal) and server.log for visibility
log_to_server() {
  local line="$*"
  local server_log="${ROOT_DIR}/server.log"
  log_info "${line}"
  echo "${line}" >> "${server_log}"
}

write_lock() {
  echo "$$" > "${WARMUP_LOCK_FILE}"
}

# shellcheck disable=SC2329
cleanup_lock() {
  rm -f "${WARMUP_LOCK_FILE}" || true
}

trim_string() {
  local value="${1:-}"
  value="${value#${value%%[![:space:]]*}}"
  value="${value%${value##*[![:space:]]}}"
  echo "${value}"
}

add_persona_variant() {
  local gender
  local personality
  gender="$(trim_string "${1:-}")"
  personality="$(trim_string "${2:-}")"
  if [ -z "${gender}" ]; then
    return
  fi
  WARMUP_PERSONA_VARIANTS+=("${gender}|${personality}")
}

parse_persona_spec() {
  local spec="${1:-}"
  local entries
  IFS=',' read -r -a entries <<<"${spec}"
  for entry in "${entries[@]}"; do
    entry="$(trim_string "${entry}")"
    if [ -z "${entry}" ]; then
      continue
    fi
    if [[ "${entry}" == *:* ]]; then
      add_persona_variant "${entry%%:*}" "${entry#*:}"
    else
      add_persona_variant "${entry}" ""
    fi
  done
}

# Build persona variants from env overrides or repo defaults.
detect_persona_variants() {
  WARMUP_PERSONA_VARIANTS=()

  if [ -n "${WARMUP_PERSONAS:-}" ]; then
    parse_persona_spec "${WARMUP_PERSONAS}"
    return
  fi

  if [ -n "${GENDER:-}" ]; then
    add_persona_variant "${GENDER}" "${PERSONALITY:-}"
    return
  fi

  local py_output=""
  if py_output="$("${PY_BIN}" - <<'PY' 2>/dev/null
from tests.config.defaults import PERSONA_VARIANTS
for gender, personality, _ in PERSONA_VARIANTS:
    if not gender:
        continue
    personality = personality or ""
    print(f"{gender}:{personality}")
PY
)"; then
    while IFS= read -r line; do
      line="$(trim_string "${line}")"
      if [ -z "${line}" ]; then
        continue
      fi
      if [[ "${line}" == *:* ]]; then
        add_persona_variant "${line%%:*}" "${line#*:}"
      else
        add_persona_variant "${line}" ""
      fi
    done <<<"${py_output}"
  fi

  if [ "${#WARMUP_PERSONA_VARIANTS[@]}" -eq 0 ]; then
    add_persona_variant "female" ""
    add_persona_variant "male" ""
  fi
}

sanitize_label() {
  local value="${1:-}"
  value="${value,,}"
  value="${value//[^a-z0-9]/_}"
  echo "${value}"
}

safe_log_prefix() {
  local raw="${1:-run}"
  local cleaned
  cleaned="$(sanitize_label "${raw}")"
  if [ -z "${cleaned}" ]; then
    cleaned="run"
  fi
  echo "${cleaned}"
}

log_phase_result() {
  local label="${1:-}"
  local status="${2:-}"
  local log_path="${3:-}"
  if [ "${status}" = "OK" ]; then
    log_to_server "[warmup] ${label} (OK)"
  else
    if [ -n "${log_path}" ]; then
      log_to_server "[warmup] ${label} (FAIL) (see ${log_path})"
    else
      log_to_server "[warmup] ${label} (FAIL)"
    fi
  fi
}

choose_python() {
  local venv_py=""
  if command -v get_venv_python >/dev/null 2>&1; then
    venv_py="$(get_venv_python 2>/dev/null || true)"
  elif command -v get_venv_dir >/dev/null 2>&1; then
    local fallback_dir
    fallback_dir="$(get_venv_dir)"
    venv_py="${fallback_dir}/bin/python"
  fi
  if [ -n "${venv_py}" ] && [ -x "${venv_py}" ]; then
    echo "${venv_py}"
    return 0
  fi

  if command -v get_python_binary_for_engine >/dev/null 2>&1; then
    local engine_py
    engine_py="$(get_python_binary_for_engine 2>/dev/null || true)"
    if [ -n "${engine_py}" ] && command -v "${engine_py}" >/dev/null 2>&1; then
      command -v "${engine_py}"
      return 0
    fi
  fi

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

# Activate venv if available (non-fatal)
activate_venv "" 0 || true

if ! PY_BIN="$(choose_python)"; then
  log_to_server "[warmup] ✗ Unable to locate python interpreter."
  exit 1
fi

PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONPATH

wait_for_ready() {
  local deadline=$((SECONDS + WARMUP_TIMEOUT_SECS))
  local urls=("${SERVER_HEALTH_URLS[@]}")
  while (( SECONDS <= deadline )); do
    if bash "${WARMUP_HEALTH_CHECK_SCRIPT}" "${urls[@]}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${WARMUP_HEALTH_POLL_INTERVAL_SECS}"
  done
  return 1
}

# Detect the maximum connection count from env overrides or config fallback.
detect_max_conn() {
  if [[ -n "${MAX_CONCURRENT_CONNECTIONS:-}" ]]; then
    echo "${MAX_CONCURRENT_CONNECTIONS}"
    return 0
  fi

  local py_output
  if py_output="$("${PY_BIN}" -c "
import sys
import os
sys.path.insert(0, '${ROOT_DIR}')
from src.config.limits import MAX_CONCURRENT_CONNECTIONS
print(MAX_CONCURRENT_CONNECTIONS)
" 2>/dev/null)"; then
    if [[ -n "${py_output}" && "${py_output}" =~ ^[0-9]+$ ]]; then
      echo "${py_output}"
      return 0
    fi
  fi

  return 1
}

# Infer which prompt template to use so warmup exercises the deployed subset.
detect_prompt_mode() {
  local deploy_mode="${DEPLOY_MODE:-}"
  case "${deploy_mode}" in
    chat) echo "chat"; return 0 ;;
    tool) echo "tool"; return 0 ;;
  esac

  local chat_flag="${DEPLOY_CHAT:-}"
  local tool_flag="${DEPLOY_TOOL:-}"
  if [[ "${chat_flag}" = "1" && "${tool_flag}" = "1" ]]; then
    echo "both"
  elif [[ "${chat_flag}" = "1" ]]; then
    echo "chat"
  elif [[ "${tool_flag}" = "1" ]]; then
    echo "tool"
  else
    echo "both"
  fi
}

# Execute a warmup/bench python helper and tee stdout/stderr into a log file.
run_py_tool() {
  local log_path="$1"; shift
  if "${PY_BIN}" "$@" >"${log_path}" 2>&1; then
    return 0
  fi
  return 1
}

# Execute a python helper with retries, logging only the final status.
run_with_retries() {
  local label="${1:-}"
  local log_prefix="${2:-run}"
  shift 2
  local -a cmd=("$@")
  local attempt=1
  local run_log=""
  local last_log=""

  for (( attempt=1; attempt<=WARMUP_RETRIES; attempt++ )); do
    run_log="${LOG_DIR}/${log_prefix}_attempt${attempt}.log"
    last_log="${run_log}"
    log_warmup "${label}: attempt ${attempt} → ${run_log}"
    if run_py_tool "${run_log}" "${cmd[@]}"; then
      log_phase_result "${label}" "OK"
      return 0
    fi
    log_warmup "${label}: attempt ${attempt} failed (see ${run_log})"
  done

  log_phase_result "${label}" "FAIL" "${last_log}"
  return 1
}

write_lock
trap cleanup_lock EXIT INT TERM

log_warmup_file "Waiting for server readiness on ${SERVER_ADDR} (timeout ${WARMUP_TIMEOUT_SECS}s)..."
if ! wait_for_ready; then
  log_to_server "[warmup] ✗ Server did not become healthy within ${WARMUP_TIMEOUT_SECS}s"
  exit 1
fi

if ! max_conn="$(detect_max_conn)"; then
  max_conn=""
fi
if [[ -z "${max_conn}" || "${max_conn}" =~ [^0-9] ]]; then
  log_warmup_file "MAX_CONCURRENT_CONNECTIONS not set or invalid, defaulting to ${WARMUP_DEFAULT_CONN_FALLBACK}"
  max_conn="${WARMUP_DEFAULT_CONN_FALLBACK}"
fi
if (( max_conn <= 0 )); then
  log_warmup_file "MAX_CONCURRENT_CONNECTIONS is <= 0, defaulting to ${WARMUP_DEFAULT_CONN_FALLBACK}"
  max_conn="${WARMUP_DEFAULT_CONN_FALLBACK}"
fi

log_warmup_file "Using MAX_CONCURRENT_CONNECTIONS=${max_conn} for benchmark tests"

overall_ok=1
prompt_mode="$(detect_prompt_mode)"
PROMPT_MODE_FLAGS=()
if [[ "${prompt_mode}" == "tool" ]]; then
  PROMPT_MODE_FLAGS=(--no-chat-prompt)
fi
log_warmup_file "Using prompt mode '${prompt_mode}' for warmup + bench tests"

detect_persona_variants
for persona in "${WARMUP_PERSONA_VARIANTS[@]}"; do
  IFS='|' read -r persona_gender persona_personality <<<"${persona}"
  log_warmup_file "Persona variant configured: gender=${persona_gender:-default} personality=${persona_personality:-}"
done

cd "${ROOT_DIR}"

for persona in "${WARMUP_PERSONA_VARIANTS[@]}"; do
  IFS='|' read -r persona_gender persona_personality <<<"${persona}"
  persona_gender="$(trim_string "${persona_gender}")"
  persona_personality="$(trim_string "${persona_personality}")"
  persona_label="${persona_gender:-default}"

  persona_args=()
  if [ -n "${persona_gender}" ]; then
    persona_args+=("--gender" "${persona_gender}")
  fi
  if [ -n "${persona_personality}" ]; then
    persona_args+=("--personality" "${persona_personality}")
  fi

  warmup_label="warmup: ${persona_label}"
  warmup_prefix="$(safe_log_prefix "warmup_${persona_label}")"
  if ! run_with_retries "${warmup_label}" "${warmup_prefix}" "tests/warmup.py" "${PROMPT_MODE_FLAGS[@]}" "${persona_args[@]}"; then
    overall_ok=0
  fi
  sleep "${WARMUP_RUN_DELAY_SECS}"

  bench_label="warmup: bench ${max_conn}x ${persona_label}"
  bench_prefix="$(safe_log_prefix "bench_${max_conn}x_${persona_label}")"
  if ! run_with_retries \
    "${bench_label}" \
    "${bench_prefix}" \
    "tests/bench.py" \
    "${PROMPT_MODE_FLAGS[@]}" \
    "--requests" "${max_conn}" \
    "--concurrency" "${max_conn}" \
    "${persona_args[@]}"; then
    overall_ok=0
  fi
  sleep "${WARMUP_RUN_DELAY_SECS}"
done

if [[ "${overall_ok}" -eq 1 ]]; then
  log_to_server "[warmup] ✓ Warmup + bench complete."
  exit 0
fi

log_to_server "[warmup] Warmup finished with failures."
exit 1
