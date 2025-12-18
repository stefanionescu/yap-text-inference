#!/usr/bin/env bash

# Utilities for preserving user-provided env overrides across restart flows.

RESTART_RUNTIME_SNAPSHOT_DIRTY=${RESTART_RUNTIME_SNAPSHOT_DIRTY:-0}

restart_capture_user_env() {
  local var_name="$1"
  local has_flag="RESTART_USER_OVERRIDE_HAS_${var_name}"
  local value_key="RESTART_USER_OVERRIDE_VALUE_${var_name}"

  if [ "${!var_name+x}" = "x" ]; then
    eval "${has_flag}=1"
    printf -v "${value_key}" "%s" "${!var_name}"
  else
    eval "${has_flag}=0"
    eval "${value_key}="
  fi
}

restart_restore_user_env() {
  local var_name="$1"
  local has_flag="RESTART_USER_OVERRIDE_HAS_${var_name}"
  local value_key="RESTART_USER_OVERRIDE_VALUE_${var_name}"
  local has_override
  local override_value

  eval "has_override=\${${has_flag}:-0}"
  if [ "${has_override}" != "1" ]; then
    return
  fi

  eval "override_value=\${${value_key}:-}"
  printf -v "${var_name}" "%s" "${override_value}"
  export "${var_name?}"
}

restart_set_snapshot_value() {
  local var_name="$1"
  local value="$2"
  printf -v "RESTART_SNAPSHOT_VALUE_${var_name}" "%s" "${value}"
}

restart_snapshot_value_from_env_file() {
  local var_name="$1"
  local env_file="$2"
  local extracted=""

  if [ -f "${env_file}" ]; then
    extracted="$(grep -E "^${var_name}=" "${env_file}" | tail -n1 | cut -d'=' -f2- || true)"
  fi

  restart_set_snapshot_value "${var_name}" "${extracted}"
}

restart_mark_override_if_changed() {
  local var_name="$1"
  local human_label="${2:-$1}"
  local has_flag="RESTART_USER_OVERRIDE_HAS_${var_name}"
  local value_key="RESTART_USER_OVERRIDE_VALUE_${var_name}"
  local has_override snapshot_value user_value

  eval "has_override=\${${has_flag}:-0}"
  if [ "${has_override}" != "1" ]; then
    return
  fi

  eval "snapshot_value=\${RESTART_SNAPSHOT_VALUE_${var_name}:-}"
  eval "user_value=\${${value_key}:-}"

  if [ "${snapshot_value}" != "${user_value}" ]; then
    log_info "[restart] Override detected for ${human_label}: stored='${snapshot_value:-<unset>}' new='${user_value}'"
    RESTART_RUNTIME_SNAPSHOT_DIRTY=1
  fi
}
