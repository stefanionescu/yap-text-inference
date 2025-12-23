#!/usr/bin/env bash
# =============================================================================
# Dependency Version Checking Utilities
# =============================================================================
# Provides functions to check if dependencies are already installed with the
# correct versions, avoiding redundant reinstalls unless forced.
#
# Usage: source "scripts/lib/deps/check.sh"
# =============================================================================

# =============================================================================
# Helper Functions
# =============================================================================

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

# =============================================================================
# Python Package Version Checks
# =============================================================================

# Minimal venv existence check (no dependency on other helpers)
check_venv_exists() {
  local venv_dir="${1:-${VENV_DIR:-${ROOT_DIR}/.venv}}"

  if [[ ! -d "$venv_dir" ]]; then
    return 1
  fi
  if [[ ! -f "$venv_dir/bin/python" ]]; then
    return 1
  fi
  if [[ ! -f "$venv_dir/bin/activate" ]]; then
    return 1
  fi
  return 0
}

# Log a human-readable summary of current TRT dep status
log_trt_dep_status() {
  local venv_dir="${1:-${VENV_DIR:-${ROOT_DIR}/.venv}}"
  echo "[deps] Status for venv=${venv_dir}"
  echo "[deps]   torch:         NEEDS_PYTORCH=${NEEDS_PYTORCH}"
  echo "[deps]   torchvision:   NEEDS_TORCHVISION=${NEEDS_TORCHVISION}"
  echo "[deps]   tensorrt_llm:  NEEDS_TRTLLM=${NEEDS_TRTLLM}"
  echo "[deps]   requirements:  NEEDS_REQUIREMENTS=${NEEDS_REQUIREMENTS}"
  if [[ ${#REQUIREMENTS_MISSING_PKGS[@]:-0} -gt 0 ]]; then
    echo "[deps]   Missing pkgs: ${REQUIREMENTS_MISSING_PKGS[*]}"
  fi
  if [[ ${#REQUIREMENTS_WRONG_VERSION_PKGS[@]:-0} -gt 0 ]]; then
    echo "[deps]   Wrong version pkgs: ${REQUIREMENTS_WRONG_VERSION_PKGS[*]}"
  fi
}

# Check if PyTorch is installed with correct version (exact match, including CUDA suffix)
# Returns: 0 if correct, 1 if missing, 2 if wrong version
check_pytorch_installed() {
  local required_version="${1:-2.9.0}"
  local py_exe="${2:-python}"
  
  local installed_ver
  installed_ver=$(get_pip_pkg_version "torch" "$py_exe")
  
  if [[ -z "$installed_ver" ]]; then
    log_info "[deps] PyTorch is NOT installed"
    return 1
  fi
  
  if [[ "$installed_ver" != "$required_version" ]]; then
    log_info "[deps] PyTorch version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi
  
  log_info "[deps] PyTorch OK: $installed_ver"
  return 0
}

# Check if TorchVision is installed with correct version (exact match)
# Returns: 0 if correct, 1 if missing, 2 if wrong version
check_torchvision_installed() {
  local required_version="${1:-0.24.0}"
  local py_exe="${2:-python}"
  
  local installed_ver
  installed_ver=$(get_pip_pkg_version "torchvision" "$py_exe")
  
  if [[ -z "$installed_ver" ]]; then
    log_info "[deps] TorchVision is NOT installed"
    return 1
  fi
  
  if [[ "$installed_ver" != "$required_version" ]]; then
    log_info "[deps] TorchVision version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi
  
  log_info "[deps] TorchVision OK: $installed_ver"
  return 0
}

# Check if TensorRT-LLM is installed with correct version
# Returns: 0 if correct, 1 if missing, 2 if wrong version
check_trtllm_installed() {
  local required_version="${1:-1.2.0rc5}"
  local py_exe="${2:-python}"
  
  local installed_ver
  installed_ver=$(get_pip_pkg_version "tensorrt_llm" "$py_exe")
  
  if [[ -z "$installed_ver" ]]; then
    log_info "[deps] TensorRT-LLM is NOT installed"
    return 1
  fi
  
  if [[ "$installed_ver" != "$required_version" ]]; then
    log_info "[deps] TensorRT-LLM version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi
  
  log_info "[deps] TensorRT-LLM OK: $installed_ver"
  return 0
}

# Check if requirements.txt packages are installed with correct versions
# Returns: 0 if all OK, 1 if some missing, 2 if some wrong version
# Also sets REQUIREMENTS_MISSING_PKGS and REQUIREMENTS_WRONG_VERSION_PKGS arrays
check_requirements_installed() {
  local requirements_file="${1:-requirements.txt}"
  local py_exe="${2:-python}"
  
  # Resolve path relative to ROOT_DIR if not absolute
  if [[ ! "$requirements_file" = /* ]]; then
    requirements_file="${ROOT_DIR}/${requirements_file}"
  fi
  
  if [[ ! -f "$requirements_file" ]]; then
    log_info "[deps] requirements.txt not found: $requirements_file"
    return 1
  fi
  
  REQUIREMENTS_MISSING_PKGS=()
  REQUIREMENTS_WRONG_VERSION_PKGS=()
  REQUIREMENTS_MISSING=false
  REQUIREMENTS_WRONG=false
  local has_missing=false
  local has_wrong_version=false
  
  # Parse requirements.txt and check each pinned package
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    
    # Extract package name and version from lines like "package==1.2.3" or "package[extra]==1.2.3"
    if [[ "$line" =~ ^([a-zA-Z0-9_-]+)(\[[^\]]+\])?==([0-9][^[:space:]]*) ]]; then
      local pkg_name="${BASH_REMATCH[1]}"
      local required_ver="${BASH_REMATCH[3]}"
      
      # Normalize package name (replace - with _ for pip compatibility)
      local pkg_normalized="${pkg_name//-/_}"
      
      # Get installed version
      local installed_ver
      installed_ver=$(get_pip_pkg_version "$pkg_normalized" "$py_exe")
      
      if [[ -z "$installed_ver" ]]; then
        # Try with original name (some packages use dashes)
        installed_ver=$(get_pip_pkg_version "$pkg_name" "$py_exe")
      fi
      
      if [[ -z "$installed_ver" ]]; then
        REQUIREMENTS_MISSING_PKGS+=("$pkg_name==$required_ver")
        has_missing=true
        REQUIREMENTS_MISSING=true
      elif [[ "$installed_ver" != "$required_ver" ]]; then
        REQUIREMENTS_WRONG_VERSION_PKGS+=("$pkg_name")
        has_wrong_version=true
        REQUIREMENTS_WRONG=true
      fi
    fi
  done < "$requirements_file"
  
  if $has_missing; then
    log_info "[deps] Missing packages: ${REQUIREMENTS_MISSING_PKGS[*]}"
    return 1
  fi
  
  if $has_wrong_version; then
    log_info "[deps] Wrong version packages: ${REQUIREMENTS_WRONG_VERSION_PKGS[*]}"
    return 2
  fi
  
  log_info "[deps] All requirements.txt packages OK"
  return 0
}

# Uninstall packages that have wrong versions before reinstalling
uninstall_wrong_requirements_packages() {
  local py_exe="${1:-python}"
  
  if [[ ${#REQUIREMENTS_WRONG_VERSION_PKGS[@]} -gt 0 ]]; then
    log_info "[deps] Uninstalling wrong version packages: ${REQUIREMENTS_WRONG_VERSION_PKGS[*]}"
    for pkg in "${REQUIREMENTS_WRONG_VERSION_PKGS[@]}"; do
      $py_exe -m pip uninstall -y "$pkg" 2>/dev/null || true
    done
  fi
}

# Uninstall a pip package if installed with wrong version
# Usage: uninstall_pip_pkg_if_wrong_version "package" "required_version" [python_exe]
uninstall_pip_pkg_if_wrong_version() {
  local pkg="$1"
  local required_version="$2"
  local py_exe="${3:-python}"
  
  local installed_ver
  installed_ver=$(get_pip_pkg_version "$pkg" "$py_exe")
  
  if [[ -z "$installed_ver" ]]; then
    return 0  # Not installed, nothing to uninstall
  fi
  
  local installed_base="${installed_ver%%+*}"
  local required_base="${required_version%%+*}"
  
  if [[ "$installed_base" != "$required_base" ]]; then
    log_info "[deps] Uninstalling $pkg $installed_ver (need $required_version)"
    $py_exe -m pip uninstall -y "$pkg" 2>/dev/null || true
    return 0
  fi
  
  return 1  # Correct version, no uninstall needed
}

# =============================================================================
# Combined Check Functions
# =============================================================================

# Check all TRT Python dependencies in a venv
# Sets NEEDS_PYTORCH, NEEDS_TORCHVISION, NEEDS_TRTLLM, NEEDS_REQUIREMENTS globals
# Returns: 0 if all satisfied, 1 if any missing
check_trt_deps_status() {
  local venv_dir="${1:-${VENV_DIR:-${ROOT_DIR}/.venv}}"
  local pytorch_ver="${2:-2.9.0}"
  local torchvision_ver="${3:-0.24.0}"
  local trtllm_ver="${4:-1.2.0rc5}"
  local req_file="${5:-requirements-trt.txt}"
  
  NEEDS_PYTORCH=1
  NEEDS_TORCHVISION=1
  NEEDS_TRTLLM=1
  NEEDS_REQUIREMENTS=1
  
  if ! check_venv_exists "${venv_dir}" 2>/dev/null; then
    return 1
  fi
  
  local venv_py="${venv_dir}/bin/python"
  
  if check_pytorch_installed "${pytorch_ver}" "${venv_py}"; then
    NEEDS_PYTORCH=0
  fi
  
  if check_torchvision_installed "${torchvision_ver}" "${venv_py}"; then
    NEEDS_TORCHVISION=0
  fi
  
  if check_trtllm_installed "${trtllm_ver}" "${venv_py}"; then
    NEEDS_TRTLLM=0
  fi
  
  if check_requirements_installed "${req_file}" "${venv_py}"; then
    NEEDS_REQUIREMENTS=0
  fi
  
  # Return 0 if all satisfied
  if [[ "$NEEDS_PYTORCH" == "0" && "$NEEDS_TORCHVISION" == "0" && "$NEEDS_TRTLLM" == "0" && "$NEEDS_REQUIREMENTS" == "0" ]]; then
    return 0
  fi
  
  return 1
}

