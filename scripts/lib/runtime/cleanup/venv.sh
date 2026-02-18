#!/usr/bin/env bash
# =============================================================================
# Runtime Cleanup - Virtual Environments
# =============================================================================

cleanup_venvs() {
  local root_dir="$1"

  local detected_venv
  detected_venv="$(get_venv_dir)"
  if [ -n "${detected_venv}" ] && [ -d "${detected_venv}" ]; then
    log_info "[cleanup] Removing detected venv: ${detected_venv}"
    rm -rf "${detected_venv}" || true
  fi

  local quant_venv
  quant_venv="${QUANT_VENV_DIR:-$(get_quant_venv_dir)}"
  if [ -n "${quant_venv}" ] && [ -d "${quant_venv}" ]; then
    log_info "[cleanup] Removing quantization venv: ${quant_venv}"
    rm -rf "${quant_venv}" || true
  fi

  _cleanup_remove_dirs \
    "${root_dir}/.venv" \
    "${root_dir}/.venv-trt" \
    "${root_dir}/.venv-vllm" \
    "${root_dir}/.venv-quant" \
    "${root_dir}/venv" \
    "${root_dir}/env" \
    "${root_dir}/.env"

  if [ -d "/opt/venv" ]; then
    log_info "[cleanup] Removing Docker venv: /opt/venv"
    rm -rf "/opt/venv" || true
  fi
  if [ -d "/opt/venv-quant" ]; then
    log_info "[cleanup] Removing Docker quant venv: /opt/venv-quant"
    rm -rf "/opt/venv-quant" || true
  fi
}

cleanup_engine_artifacts() {
  local root_dir="$1"
  cleanup_repo_engine_artifacts "${root_dir}"
  cleanup_repo_runtime_caches "${root_dir}"
  cleanup_venvs "${root_dir}"
}
