#!/usr/bin/env bash
# =============================================================================
# Dependency Version Checking and Caching Utilities
# =============================================================================
# Provides functions to check if dependencies are already installed with the
# correct versions, avoiding redundant reinstalls unless forced.
#
# Usage: source "scripts/lib/deps.sh"
# =============================================================================

# =============================================================================
# Version References
# =============================================================================
# These are derived from variables exported by scripts/lib/environment.sh
# Do NOT hardcode versions here - they come from environment.sh

# Extract base versions (strip CUDA suffix like +cu130)
# These are used for version comparison in check functions
_get_pytorch_base_version() {
  echo "${PYTORCH_VERSION%%+*}"
}

_get_torchvision_base_version() {
  echo "${TORCHVISION_VERSION%%+*}"
}

_get_trtllm_version() {
  echo "${TRTLLM_PIP_SPEC##*==}"
}

_get_mpi_version_prefix() {
  echo "${MPI_VERSION_PIN%%-*}"
}

# =============================================================================
# Helper Functions
# =============================================================================

_deps_log() {
  echo "[deps] $*"
}

_deps_warn() {
  echo "[deps] WARN: $*" >&2
}

_deps_error() {
  echo "[deps] ERROR: $*" >&2
}

# Extract version from apt package (e.g., "4.1.6-7ubuntu2" -> "4.1.6")
_extract_apt_version_prefix() {
  local full_version="$1"
  echo "${full_version%%-*}"
}

# Compare version strings (returns 0 if $1 >= $2)
_version_gte() {
  local v1="$1" v2="$2"
  # Use sort -V for version comparison
  [[ "$(printf '%s\n%s' "$v1" "$v2" | sort -V | head -n1)" == "$v2" ]]
}

# =============================================================================
# System Package (APT) Checks
# =============================================================================

# Check if an apt package is installed
# Usage: is_apt_pkg_installed "package-name"
is_apt_pkg_installed() {
  local pkg="$1"
  dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"
}

# Get installed version of an apt package
# Usage: get_apt_pkg_version "package-name"
get_apt_pkg_version() {
  local pkg="$1"
  dpkg-query -W -f='${Version}' "$pkg" 2>/dev/null || echo ""
}

# Check if MPI packages are installed with correct version
# Returns 0 if all MPI packages are installed with matching version prefix
check_mpi_deps_installed() {
  local required_prefix="${1:-$(_get_mpi_version_prefix)}"
  local mpi_pkg=""
  
  # Determine which MPI package name to use based on what's installed
  # Check both possible package names and use whichever is installed
  # On Ubuntu 24.04+, libopenmpi3t64 is the correct package name
  # On older Ubuntu, libopenmpi3 is used
  if is_apt_pkg_installed "libopenmpi3t64"; then
    mpi_pkg="libopenmpi3t64"
  elif is_apt_pkg_installed "libopenmpi3"; then
    mpi_pkg="libopenmpi3"
  else
    # Neither is installed - try to determine which one should be used
    # Check apt-cache to see what's available (like bootstrap.sh does)
    if command -v apt-cache >/dev/null 2>&1; then
      if apt-cache policy libopenmpi3t64 >/dev/null 2>&1; then
        if apt-cache policy libopenmpi3t64 | grep -q "Candidate:"; then
          mpi_pkg="libopenmpi3t64"
        fi
      fi
    fi
    # Default to libopenmpi3 if we couldn't determine
    mpi_pkg="${mpi_pkg:-libopenmpi3}"
  fi
  
  local pkgs=("$mpi_pkg" "openmpi-bin" "openmpi-common")
  local all_present=true
  local all_correct_version=true
  
  for pkg in "${pkgs[@]}"; do
    if ! is_apt_pkg_installed "$pkg"; then
      _deps_log "MPI package '$pkg' is NOT installed"
      all_present=false
    else
      local installed_ver
      installed_ver=$(get_apt_pkg_version "$pkg")
      local installed_prefix
      installed_prefix=$(_extract_apt_version_prefix "$installed_ver")
      
      if [[ "$installed_prefix" != "${required_prefix%%-*}" ]]; then
        _deps_log "MPI package '$pkg' version mismatch: installed=$installed_ver, required prefix=$required_prefix"
        all_correct_version=false
      else
        _deps_log "MPI package '$pkg' OK: $installed_ver"
      fi
    fi
  done
  
  if $all_present && $all_correct_version; then
    return 0
  fi
  return 1
}

# Check if Python dev packages are installed
check_python_dev_installed() {
  local py_version="${1:-${PYTHON_VERSION:-3.10}}"
  local pkgs=("python${py_version}-venv" "python${py_version}-dev")
  
  for pkg in "${pkgs[@]}"; do
    if ! is_apt_pkg_installed "$pkg"; then
      _deps_log "Python dev package '$pkg' is NOT installed"
      return 1
    else
      _deps_log "Python dev package '$pkg' OK"
    fi
  done
  
  return 0
}

# Check if basic system utilities are installed
check_system_utils_installed() {
  local pkgs=("git" "wget" "curl" "jq")
  
  for pkg in "${pkgs[@]}"; do
    if ! command -v "$pkg" >/dev/null 2>&1; then
      _deps_log "System utility '$pkg' is NOT installed"
      return 1
    else
      _deps_log "System utility '$pkg' OK"
    fi
  done
  
  return 0
}

# =============================================================================
# Python Environment Checks
# =============================================================================

# Check if a valid venv exists at the specified path
# Usage: check_venv_exists "/path/to/.venv"
check_venv_exists() {
  local venv_dir="${1:-${VENV_DIR:-$PWD/.venv}}"
  
  if [[ ! -d "$venv_dir" ]]; then
    _deps_log "Virtual environment does not exist: $venv_dir"
    return 1
  fi
  
  if [[ ! -f "$venv_dir/bin/activate" ]]; then
    _deps_log "Virtual environment is corrupted (no activate script): $venv_dir"
    return 1
  fi
  
  if [[ ! -f "$venv_dir/bin/python" ]]; then
    _deps_log "Virtual environment is corrupted (no python): $venv_dir"
    return 1
  fi
  
  _deps_log "Virtual environment OK: $venv_dir"
  return 0
}

# Get installed pip package version
# Must be called with venv activated or specify python path
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

# Check if PyTorch is installed with correct version
# Must be called with venv activated
check_pytorch_installed() {
  local required_version="${1:-$(_get_pytorch_base_version)}"
  local py_exe="${2:-python}"
  
  local installed_ver
  installed_ver=$(get_pip_pkg_version "torch" "$py_exe")
  
  if [[ -z "$installed_ver" ]]; then
    _deps_log "PyTorch is NOT installed"
    return 1
  fi
  
  # Strip CUDA suffix for comparison (e.g., "2.9.1+cu130" -> "2.9.1")
  local installed_base="${installed_ver%%+*}"
  local required_base="${required_version%%+*}"
  
  if [[ "$installed_base" != "$required_base" ]]; then
    _deps_log "PyTorch version mismatch: installed=$installed_ver, required=$required_version"
    return 2  # Wrong version - needs uninstall + reinstall
  fi
  
  _deps_log "PyTorch OK: $installed_ver"
  return 0
}

# Check if TorchVision is installed with correct version
check_torchvision_installed() {
  local required_version="${1:-$(_get_torchvision_base_version)}"
  local py_exe="${2:-python}"
  
  local installed_ver
  installed_ver=$(get_pip_pkg_version "torchvision" "$py_exe")
  
  if [[ -z "$installed_ver" ]]; then
    _deps_log "TorchVision is NOT installed"
    return 1
  fi
  
  local installed_base="${installed_ver%%+*}"
  local required_base="${required_version%%+*}"
  
  if [[ "$installed_base" != "$required_base" ]]; then
    _deps_log "TorchVision version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi
  
  _deps_log "TorchVision OK: $installed_ver"
  return 0
}

# Check if TensorRT-LLM is installed with correct version
check_trtllm_installed() {
  local required_version="${1:-$(_get_trtllm_version)}"
  local py_exe="${2:-python}"
  
  local installed_ver
  installed_ver=$(get_pip_pkg_version "tensorrt_llm" "$py_exe")
  
  if [[ -z "$installed_ver" ]]; then
    _deps_log "TensorRT-LLM is NOT installed"
    return 1
  fi
  
  if [[ "$installed_ver" != "$required_version" ]]; then
    _deps_log "TensorRT-LLM version mismatch: installed=$installed_ver, required=$required_version"
    return 2
  fi
  
  _deps_log "TensorRT-LLM OK: $installed_ver"
  return 0
}

# Check if requirements.txt packages are installed with correct versions
# Returns:
#   0 = all packages installed with correct versions
#   1 = some packages missing
#   2 = some packages have wrong versions
# Also sets REQUIREMENTS_MISSING_PKGS and REQUIREMENTS_WRONG_VERSION_PKGS arrays
check_requirements_installed() {
  local requirements_file="${1:-requirements.txt}"
  local py_exe="${2:-python}"
  
  if [[ ! -f "$requirements_file" ]]; then
    _deps_log "requirements.txt not found: $requirements_file"
    return 1
  fi
  
  REQUIREMENTS_MISSING_PKGS=()
  REQUIREMENTS_WRONG_VERSION_PKGS=()
  local has_missing=false
  local has_wrong_version=false
  
  # Parse requirements.txt and check each pinned package
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    
    # Skip lines with extras like uvicorn[standard]
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
        _deps_log "Package '$pkg_name' is NOT installed (need $required_ver)"
        REQUIREMENTS_MISSING_PKGS+=("$pkg_name==$required_ver")
        has_missing=true
      elif [[ "$installed_ver" != "$required_ver" ]]; then
        _deps_log "Package '$pkg_name' version mismatch: installed=$installed_ver, required=$required_ver"
        REQUIREMENTS_WRONG_VERSION_PKGS+=("$pkg_name")
        has_wrong_version=true
      fi
    fi
  done < "$requirements_file"
  
  if $has_missing; then
    _deps_log "Missing packages: ${REQUIREMENTS_MISSING_PKGS[*]}"
    return 1
  fi
  
  if $has_wrong_version; then
    _deps_log "Wrong version packages: ${REQUIREMENTS_WRONG_VERSION_PKGS[*]}"
    return 2
  fi
  
  _deps_log "All requirements.txt packages OK"
  return 0
}

# Uninstall packages that have wrong versions before reinstalling
uninstall_wrong_requirements_packages() {
  local py_exe="${1:-python}"
  
  if [[ ${#REQUIREMENTS_WRONG_VERSION_PKGS[@]} -gt 0 ]]; then
    _deps_log "Uninstalling wrong version packages: ${REQUIREMENTS_WRONG_VERSION_PKGS[*]}"
    for pkg in "${REQUIREMENTS_WRONG_VERSION_PKGS[@]}"; do
      $py_exe -m pip uninstall -y "$pkg" 2>/dev/null || true
    done
  fi
}

# =============================================================================
# Combined Checks
# =============================================================================

# Check all system (apt) dependencies
# Returns 0 if all installed, 1 if any missing/wrong version
check_all_system_deps() {
  local force="${FORCE_INSTALL_DEPS:-0}"
  
  if [[ "$force" == "1" ]]; then
    _deps_log "Force install requested - skipping system deps check"
    return 1
  fi
  
  local all_ok=true
  
  if ! check_system_utils_installed; then
    all_ok=false
  fi
  
  if ! check_python_dev_installed; then
    all_ok=false
  fi
  
  if ! check_mpi_deps_installed; then
    all_ok=false
  fi
  
  $all_ok
}

# Check all Python dependencies in venv
# Returns 0 if all installed with correct versions
# Usage: check_all_python_deps [venv_dir]
check_all_python_deps() {
  local venv_dir="${1:-${VENV_DIR:-$PWD/.venv}}"
  local force="${FORCE_INSTALL_DEPS:-0}"
  
  if [[ "$force" == "1" ]]; then
    _deps_log "Force install requested - skipping Python deps check"
    return 1
  fi
  
  if ! check_venv_exists "$venv_dir"; then
    return 1
  fi
  
  local py_exe="$venv_dir/bin/python"
  local all_ok=true
  
  if ! check_pytorch_installed "" "$py_exe"; then
    all_ok=false
  fi
  
  if ! check_torchvision_installed "" "$py_exe"; then
    all_ok=false
  fi
  
  if ! check_trtllm_installed "" "$py_exe"; then
    all_ok=false
  fi
  
  $all_ok
}

# =============================================================================
# Uninstall Functions
# =============================================================================

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
    _deps_log "Uninstalling $pkg $installed_ver (need $required_version)"
    $py_exe -m pip uninstall -y "$pkg" 2>/dev/null || true
    return 0
  fi
  
  return 1  # Correct version, no uninstall needed
}

# =============================================================================
# Status Summary
# =============================================================================

# Print a summary of dependency status
print_deps_status() {
  local venv_dir="${1:-${VENV_DIR:-$PWD/.venv}}"
  
  echo ""
  echo "=== Dependency Status ==="
  echo ""
  
  echo "System Packages:"
  check_system_utils_installed 2>/dev/null || true
  check_python_dev_installed 2>/dev/null || true
  check_mpi_deps_installed 2>/dev/null || true
  
  echo ""
  echo "Python Environment ($venv_dir):"
  if check_venv_exists "$venv_dir" 2>/dev/null; then
    local py_exe="$venv_dir/bin/python"
    check_pytorch_installed "" "$py_exe" 2>/dev/null || true
    check_torchvision_installed "" "$py_exe" 2>/dev/null || true
    check_trtllm_installed "" "$py_exe" 2>/dev/null || true
  fi
  
  echo ""
  echo "========================="
  echo ""
}

