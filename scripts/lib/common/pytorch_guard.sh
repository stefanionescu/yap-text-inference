#!/usr/bin/env bash

# PyTorch/TorchVision CUDA mismatch guard shared by main.sh and restart.sh.
# Detects when the packages were built against different CUDA major versions
# (which triggers a RuntimeError on import) and proactively uninstalls both so
# the next dependency install can pull matching wheels from the correct index.

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

  set +e
  detect_output=$("${py_bin}" - <<'PY' 2>&1)
import importlib.util
import sys

torch_spec = importlib.util.find_spec("torch")
if torch_spec is None:
    sys.exit(0)

import torch  # noqa: E402

vision_spec = importlib.util.find_spec("torchvision")
if vision_spec is None:
    sys.exit(0)

try:
    import torchvision  # noqa: F401,E402
except Exception as exc:  # noqa: BLE001
    message = str(exc).strip()
    needle = "PyTorch and torchvision were compiled with different CUDA major versions"
    if needle in message:
        print(message)
        torch_ver = getattr(torch, "__version__", "")
        torch_cuda = (getattr(torch.version, "cuda", "") or "").strip()
        if torch_ver:
            summary = f"torch=={torch_ver}"
            if torch_cuda:
                summary += f" (CUDA {torch_cuda})"
            print(summary)
        sys.exit(42)
    sys.exit(0)

sys.exit(0)
PY
  detect_rc=$?
  if [[ "${previous_opts}" == *e* ]]; then
    set -e
  fi

  if [ "${detect_rc}" -eq 42 ]; then
    log_warn "${prefix} ⚠ Detected PyTorch/TorchVision CUDA mismatch in ${venv_dir}"
    if [ -n "${detect_output}" ]; then
      while IFS= read -r line; do
        [ -z "${line}" ] && continue
        log_warn "${prefix}   ${line}"
      done <<< "${detect_output}"
    fi

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

    log_info "${prefix} torch/torchvision removed; next install step will pull matching wheels"
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
