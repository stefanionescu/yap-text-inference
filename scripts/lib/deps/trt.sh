#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Dependency Installation
# =============================================================================
# System dependencies and pip packages for TensorRT-LLM.

# Install system dependencies required for TensorRT-LLM
# This includes OpenMPI development libraries needed for mpi4py compilation
ensure_trt_system_deps() {
  local engine="${INFERENCE_ENGINE:-vllm}"
  
  # Only needed for TRT engine
  if [ "${engine}" != "trt" ] && [ "${engine}" != "TRT" ]; then
    return 0
  fi
  
  log_info "[deps] Checking TensorRT-LLM system dependencies..."
  
  # Check if mpi.h is already available
  if _check_mpi_headers; then
    return 0
  fi
  
  log_info "[deps] Installing MPI development libraries for mpi4py compilation..."
  
  if command -v apt-get >/dev/null 2>&1; then
    _install_mpi_apt
  elif command -v apk >/dev/null 2>&1; then
    _install_mpi_apk
  elif command -v dnf >/dev/null 2>&1; then
    _install_mpi_dnf
  elif command -v yum >/dev/null 2>&1; then
    _install_mpi_yum
  else
    log_warn "[deps] ⚠ No supported package manager found. Please install MPI development libraries manually:"
    log_warn "[deps] ⚠   Debian/Ubuntu: apt-get install libopenmpi-dev openmpi-bin"
    log_warn "[deps] ⚠   RHEL/CentOS: dnf install openmpi-devel"
    log_warn "[deps] ⚠   Alpine: apk add openmpi-dev"
    return 1
  fi
  
  # Verify installation
  if _check_mpi_headers; then
    log_info "[deps] ✓ MPI installed"
    return 0
  else
    log_err "[deps] ✗ Failed to install MPI development libraries"
    return 1
  fi
}

trt_determine_dependency_status() {
  local venv_dir="$1"
  local pytorch_ver="${2:-${TRT_PYTORCH_VERSION:-2.9.0+cu130}}"
  local torchvision_ver="${3:-${TRT_TORCHVISION_VERSION:-0.24.0+cu130}}"
  local trtllm_ver="${4:-${TRT_VERSION:-1.2.0rc5}}"
  local req_file="${5:-requirements-trt.txt}"

  if check_trt_deps_status "${venv_dir}" "${pytorch_ver}" "${torchvision_ver}" "${trtllm_ver}" "${req_file}"; then
    log_trt_dep_status "${venv_dir}"
    return 0
  fi

  log_trt_dep_status "${venv_dir}"
  return 1
}

trt_install_missing_components() {
  local had_error=0

  if [[ "${NEEDS_PYTORCH}" = "1" || "${NEEDS_TORCHVISION}" = "1" ]]; then
    if ! trt_install_pytorch; then
      had_error=1
    fi
  fi

  if [[ "${NEEDS_REQUIREMENTS}" = "1" ]]; then
    if filter_requirements_without_flashinfer && install_requirements_without_flashinfer; then
      :
    else
      had_error=1
    fi
  fi

  # Install TRT-LLM if missing OR if flashinfer is missing (allow deps so flashinfer installs)
  if [[ "${NEEDS_TRTLLM}" = "1" || "${NEEDS_FLASHINFER}" = "1" ]]; then
    # Only suppress dependencies when we aren't trying to pull flashinfer from the TRT wheel
    if [[ "${NEEDS_FLASHINFER}" = "1" ]]; then
      unset TRTLLM_NO_DEPS
    elif [[ "${NEEDS_PYTORCH}" = "0" && "${NEEDS_TORCHVISION}" = "0" ]]; then
      export TRTLLM_NO_DEPS=1
    else
      unset TRTLLM_NO_DEPS
    fi
    if ! trt_install_tensorrt_llm; then
      had_error=1
    fi
  fi

  if [ "${had_error}" = "1" ]; then
    return 1
  fi
  return 0
}

# Check if MPI headers are available
_check_mpi_headers() {
  # Check common header locations
  if [ -f "/usr/include/mpi.h" ] || \
     [ -f "/usr/include/openmpi/mpi.h" ] || \
     [ -f "/usr/include/mpich/mpi.h" ] || \
     [ -f "/usr/include/x86_64-linux-gnu/mpi/mpi.h" ] || \
     [ -f "/usr/lib/x86_64-linux-gnu/openmpi/include/mpi.h" ]; then
    return 0
  fi
  
  # Check if mpicc is available (usually means headers are installed)
  if command -v mpicc >/dev/null 2>&1; then
    return 0
  fi
  
  return 1
}

# Debian/Ubuntu installation
_install_mpi_apt() {
  log_info "[deps] Using apt-get to install MPI dependencies..."
  
  # Select correct MPI runtime package name (t64 on Ubuntu 24.04+, non-t64 otherwise)
  local MPI_PKG="libopenmpi3"
  if apt-cache policy libopenmpi3t64 >/dev/null 2>&1; then
    if apt-cache policy libopenmpi3t64 | grep -q "Candidate:"; then
      MPI_PKG="libopenmpi3t64"
    fi
  fi
  
  local MPI_VER_ARG=""
  if [ -n "${MPI_VERSION_PIN:-}" ]; then
    MPI_VER_ARG="=${MPI_VERSION_PIN}"
  fi
  
  # Try without sudo first (for container environments running as root)
  if [ "$(id -u)" = "0" ]; then
    apt-get update -y || {
      log_warn "[deps] ⚠ apt-get update failed, continuing anyway"
    }
    # Install core dependencies (no upgrades; keep CUDA/driver untouched)
    # openmpi-bin provides orted/mpirun executables required by mpi4py during quantization
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-upgrade --no-install-recommends \
      libopenmpi-dev python3-dev \
      "${MPI_PKG}${MPI_VER_ARG}" "openmpi-bin${MPI_VER_ARG}" "openmpi-common${MPI_VER_ARG}" || {
      log_warn "[deps] ⚠ Some packages failed to install via apt"
      return 1
    }
    # Hold MPI runtime to prevent drift
    apt-mark hold "$MPI_PKG" openmpi-bin openmpi-common >/dev/null 2>&1 || true
  else
    # Try with sudo
    sudo -n apt-get update -y 2>/dev/null || {
      log_warn "[deps] ⚠ apt-get update failed (may need sudo), continuing anyway"
    }
    # Install core dependencies (no upgrades; keep CUDA/driver untouched)
    # openmpi-bin provides orted/mpirun executables required by mpi4py during quantization
    sudo -n DEBIAN_FRONTEND=noninteractive apt-get install -y --no-upgrade --no-install-recommends \
      libopenmpi-dev python3-dev \
      "${MPI_PKG}${MPI_VER_ARG}" "openmpi-bin${MPI_VER_ARG}" "openmpi-common${MPI_VER_ARG}" 2>/dev/null || {
      log_warn "[deps] ⚠ Some packages failed to install via apt (may need sudo)"
      return 1
    }
    # Hold MPI runtime to prevent drift
    sudo -n apt-mark hold "$MPI_PKG" openmpi-bin openmpi-common >/dev/null 2>&1 || true
  fi
  
  return 0
}

# Alpine installation
_install_mpi_apk() {
  log_info "[deps] Using apk to install MPI dependencies..."
  
  if [ "$(id -u)" = "0" ]; then
    apk add --no-cache openmpi-dev python3-dev || return 1
  else
    sudo -n apk add --no-cache openmpi-dev python3-dev 2>/dev/null || return 1
  fi
  
  return 0
}

# RHEL/Fedora installation
_install_mpi_dnf() {
  log_info "[deps] Using dnf to install MPI dependencies..."
  
  if [ "$(id -u)" = "0" ]; then
    dnf install -y openmpi-devel python3-devel || return 1
  else
    sudo -n dnf install -y openmpi-devel python3-devel 2>/dev/null || return 1
  fi
  
  return 0
}

# CentOS/older RHEL installation  
_install_mpi_yum() {
  log_info "[deps] Using yum to install MPI dependencies..."
  
  if [ "$(id -u)" = "0" ]; then
    yum install -y openmpi-devel python3-devel || return 1
  else
    sudo -n yum install -y openmpi-devel python3-devel 2>/dev/null || return 1
  fi
  
  return 0
}

# Verify MPI runtime is functional
verify_mpi_runtime() {
  local need_mpi="${NEED_MPI:-0}"
  
  if [ "${need_mpi}" != "1" ]; then
    log_info "[deps] Skipping MPI runtime verification (NEED_MPI=0)"
    return 0
  fi
  
  log_info "[deps] Verifying MPI runtime..."
  
  # Check library path
  if ! ldconfig -p 2>/dev/null | grep -q "libmpi.so"; then
    log_warn "[deps] ⚠ libmpi.so not found in library path"
    log_warn "[deps] ⚠ Add /usr/lib/x86_64-linux-gnu to LD_LIBRARY_PATH if needed"
  fi
  
  return 0
}

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

# Main entry point for TRT-LLM dependency installation
# Call this after venv is set up and activated
# Requires: TRT_PYTORCH_VERSION, TRT_TORCHVISION_VERSION, TRT_VERSION to be set
trt_install_deps() {
  local venv_dir="${1:-${VENV_DIR:-}}"
  
  log_info "[trt] Installing TRT-LLM dependencies..."
  
  # Check existing dependency versions (sets NEEDS_* globals)
  trt_determine_dependency_status "${venv_dir}" \
    "${TRT_PYTORCH_VERSION}" \
    "${TRT_TORCHVISION_VERSION}" \
    "${TRT_VERSION:-1.2.0rc5}" \
    "requirements-trt.txt" || true
  
  # Install missing components
  if ! trt_install_missing_components; then
    log_err "[trt] ✗ Dependency installation failed"
    return 1
  fi
  
  # Validate installation
  if ! trt_validate_installation; then
    log_err "[trt] ✗ TensorRT-LLM validation failed"
    return 1
  fi
  
  # Prepare repo for quantization scripts
  if ! trt_prepare_repo; then
    log_err "[trt] ✗ TensorRT-LLM repo preparation failed"
    return 1
  fi
  
  log_info "[trt] ✓ TRT-LLM ready"
  return 0
}
