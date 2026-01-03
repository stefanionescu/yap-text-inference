#!/usr/bin/env bash
# =============================================================================
# PyTorch CUDA Mismatch Guard
# =============================================================================
# Detects PyTorch/TorchVision packages built against different CUDA versions
# and proactively uninstalls them to prevent RuntimeError on import.

# Usage: torch_cuda_mismatch_guard "[main]"  # prefix used in log output
# Sets TORCHVISION_CUDA_MISMATCH_DETECTED=1 when it removes the packages.
torch_cuda_mismatch_guard() {
  local prefix="${1:-main}"
  local venv_dir
  venv_dir="$(get_venv_dir 2>/dev/null || true)"

  if [ -z "${venv_dir}" ]; then
    return 0
  fi

  local py_bin="${venv_dir}/bin/python"
  if [ ! -x "${py_bin}" ]; then
    return 0
  fi

  local detect_output=""
  local detect_rc=0
  local previous_opts="$-"
  local tmp_output

  tmp_output=$(mktemp -t torch-guard-XXXXXX 2>/dev/null) || \
    tmp_output=$(mktemp /tmp/torch-guard-XXXXXX 2>/dev/null) || true
  if [ -z "${tmp_output}" ]; then
    tmp_output="${ROOT_DIR:-/tmp}/torch-guard-${RANDOM:-$$}"
  fi

  set +e
  PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    "${py_bin}" -m src.scripts.torch_guard >"${tmp_output}" 2>&1
  detect_rc=$?
  if [[ "${previous_opts}" == *e* ]]; then
    set -e
  fi
  detect_output=$(cat "${tmp_output}" 2>/dev/null || true)
  rm -f "${tmp_output}" 2>/dev/null || true

  if [ "${detect_rc}" -eq 42 ]; then
    log_warn "${prefix} ⚠ Detected PyTorch/TorchVision CUDA mismatch"

    TORCHVISION_CUDA_MISMATCH_DETECTED=1
    export TORCHVISION_CUDA_MISMATCH_DETECTED

    local -a pip_cmd
    if [ -x "${venv_dir}/bin/pip" ]; then
      pip_cmd=("${venv_dir}/bin/pip")
    else
      pip_cmd=("${py_bin}" -m pip)
    fi

    log_info "${prefix} Removing mismatched torch packages before reinstall..."
    if ! "${pip_cmd[@]}" uninstall -y torch torchvision >/dev/null 2>&1; then
      log_err "${prefix} ✗ Failed to uninstall mismatched torch/torchvision packages"
      log_err "${prefix}   Run: ${pip_cmd[*]} uninstall -y torch torchvision"
      return 1
    fi
    return 0
  fi

  if [ "${detect_rc}" -ne 0 ]; then
    log_warn "${prefix} ⚠ Torch/TorchVision mismatch probe failed (rc=${detect_rc})"
    if [ -n "${detect_output}" ]; then
      while IFS= read -r line; do
        [ -z "${line}" ] && continue
        log_warn "${prefix}   ${line}"
      done <<< "${detect_output}"
    fi
  fi

  return 0
}
