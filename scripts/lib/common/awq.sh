#!/usr/bin/env bash
# =============================================================================
# AWQ Cache Utilities
# =============================================================================
# Helpers for detecting and resolving cached AWQ model artifacts.

awq_chat_cache_ready() {
  local dir="$1"
  [ -d "${dir}" ] || return 1
  if [ -f "${dir}/.awq_ok" ] || [ -f "${dir}/awq_metadata.json" ] || [ -f "${dir}/awq_config.json" ]; then
    return 0
  fi
  return 1
}

awq_resolve_local_chat_cache() {
  local root_dir="$1"
  local cache_dir="${root_dir}/.awq/chat_awq"
  if awq_chat_cache_ready "${cache_dir}"; then
    echo "${cache_dir}"
    return 0
  fi
  return 1
}
