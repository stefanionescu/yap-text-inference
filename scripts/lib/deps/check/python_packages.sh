#!/usr/bin/env bash
# =============================================================================
# Dependency Check - Python Package Probes
# =============================================================================
# Package version lookups and per-package checks for TRT dependency validation.

# Get installed pip package version
# Usage: get_pip_pkg_version "package-name" [python_exe]
get_pip_pkg_version() {
  local pkg="$1"
  local py_exe="${2:-python}"

  $py_exe -c "
import sys
try:
    from importlib.metadata import version
    print(version('$pkg'))
except Exception:
    sys.exit(1)
" 2>/dev/null || echo ""
}

# Check if PyTorch is installed with correct version (exact match, including CUDA suffix)
# Returns: 0 if correct, 1 if missing, 2 if wrong version
check_pytorch_installed() {
  local required_version="${1:-${CFG_TRT_PYTORCH_VERSION}}"
  local py_exe="${2:-python}"

  local installed_ver
  installed_ver=$(get_pip_pkg_version "torch" "$py_exe")

  if [[ -z $installed_ver ]]; then
    return 1
  fi

  if [[ $installed_ver != "$required_version" ]]; then
    log_info "[deps] PyTorch version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi

  return 0
}

# Check if TorchVision is installed with correct version (exact match)
# Returns: 0 if correct, 1 if missing, 2 if wrong version
check_torchvision_installed() {
  local required_version="${1:-${CFG_TRT_TORCHVISION_VERSION}}"
  local py_exe="${2:-python}"

  local installed_ver
  installed_ver=$(get_pip_pkg_version "torchvision" "$py_exe")

  if [[ -z $installed_ver ]]; then
    return 1
  fi

  if [[ $installed_ver != "$required_version" ]]; then
    log_info "[deps] TorchVision version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi

  return 0
}

# Check if TensorRT-LLM is installed with correct version
# Returns: 0 if correct, 1 if missing, 2 if wrong version
check_trtllm_installed() {
  local required_version="${1:-${CFG_TRT_VERSION}}"
  local py_exe="${2:-python}"

  local installed_ver
  installed_ver=$(get_pip_pkg_version "tensorrt_llm" "$py_exe")

  if [[ -z $installed_ver ]]; then
    return 1
  fi

  if [[ $installed_ver != "$required_version" ]]; then
    log_info "[deps] TensorRT-LLM version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi

  return 0
}

check_flashinfer_installed() {
  local py_exe="${1:-python}"

  if flashinfer_present_py "$py_exe"; then
    return 0
  fi

  return 1
}

# Uninstall a pip package if installed with wrong version
# Usage: uninstall_pip_pkg_if_wrong_version "package" "required_version" [python_exe]
uninstall_pip_pkg_if_wrong_version() {
  local pkg="$1"
  local required_version="$2"
  local py_exe="${3:-python}"

  local installed_ver
  installed_ver=$(get_pip_pkg_version "$pkg" "$py_exe")

  if [[ -z $installed_ver ]]; then
    return 0 # Not installed, nothing to uninstall
  fi

  local installed_base="${installed_ver%%+*}"
  local required_base="${required_version%%+*}"

  if [[ $installed_base != "$required_base" ]]; then
    $py_exe -m pip uninstall -y "$pkg" 2>/dev/null || true
    return 0
  fi

  return 1 # Correct version, no uninstall needed
}
