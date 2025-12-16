#!/usr/bin/env bash

# System dependencies installation helpers
# Handles OS-level packages required for TensorRT-LLM (MPI, dev headers, etc.)

# Install system dependencies required for TensorRT-LLM
# This includes OpenMPI development libraries needed for mpi4py compilation
ensure_trt_system_deps() {
  local engine="${INFERENCE_ENGINE:-vllm}"
  
  # Only needed for TRT engine
  if [ "${engine}" != "trt" ] && [ "${engine}" != "TRT" ]; then
    return 0
  fi
  
  log_info "Checking TensorRT-LLM system dependencies..."
  
  # Check if mpi.h is already available
  if _check_mpi_headers; then
    log_info "MPI development headers already installed"
    return 0
  fi
  
  log_info "Installing MPI development libraries for mpi4py compilation..."
  
  if command -v apt-get >/dev/null 2>&1; then
    _install_mpi_apt
  elif command -v apk >/dev/null 2>&1; then
    _install_mpi_apk
  elif command -v dnf >/dev/null 2>&1; then
    _install_mpi_dnf
  elif command -v yum >/dev/null 2>&1; then
    _install_mpi_yum
  else
    log_warn "No supported package manager found. Please install MPI development libraries manually:"
    log_warn "  Debian/Ubuntu: apt-get install libopenmpi-dev openmpi-bin"
    log_warn "  RHEL/CentOS: dnf install openmpi-devel"
    log_warn "  Alpine: apk add openmpi-dev"
    return 1
  fi
  
  # Verify installation
  if _check_mpi_headers; then
    log_info "MPI development libraries installed successfully"
    return 0
  else
    log_err "Failed to install MPI development libraries"
    return 1
  fi
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
  log_info "Using apt-get to install MPI dependencies..."
  
  # Try without sudo first (for container environments running as root)
  if [ "$(id -u)" = "0" ]; then
    apt-get update -y || {
      log_warn "apt-get update failed, continuing anyway"
    }
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      libopenmpi-dev openmpi-bin python3-dev || {
      log_warn "Some packages failed to install via apt"
      return 1
    }
  else
    # Try with sudo
    sudo -n apt-get update -y 2>/dev/null || {
      log_warn "apt-get update failed (may need sudo), continuing anyway"
    }
    sudo -n DEBIAN_FRONTEND=noninteractive apt-get install -y \
      libopenmpi-dev openmpi-bin python3-dev 2>/dev/null || {
      log_warn "Some packages failed to install via apt (may need sudo)"
      return 1
    }
  fi
  
  return 0
}

# Alpine installation
_install_mpi_apk() {
  log_info "Using apk to install MPI dependencies..."
  
  if [ "$(id -u)" = "0" ]; then
    apk add --no-cache openmpi-dev python3-dev || return 1
  else
    sudo -n apk add --no-cache openmpi-dev python3-dev 2>/dev/null || return 1
  fi
  
  return 0
}

# RHEL/Fedora installation
_install_mpi_dnf() {
  log_info "Using dnf to install MPI dependencies..."
  
  if [ "$(id -u)" = "0" ]; then
    dnf install -y openmpi-devel python3-devel || return 1
  else
    sudo -n dnf install -y openmpi-devel python3-devel 2>/dev/null || return 1
  fi
  
  return 0
}

# CentOS/older RHEL installation  
_install_mpi_yum() {
  log_info "Using yum to install MPI dependencies..."
  
  if [ "$(id -u)" = "0" ]; then
    yum install -y openmpi-devel python3-devel || return 1
  else
    sudo -n yum install -y openmpi-devel python3-devel 2>/dev/null || return 1
  fi
  
  return 0
}

# Verify MPI runtime is functional
verify_mpi_runtime() {
  local need_mpi="${NEED_MPI:-1}"
  
  if [ "${need_mpi}" != "1" ]; then
    log_info "Skipping MPI runtime verification (NEED_MPI=0)"
    return 0
  fi
  
  log_info "Verifying MPI runtime..."
  
  # Check library path
  if ! ldconfig -p 2>/dev/null | grep -q "libmpi.so"; then
    log_warn "libmpi.so not found in library path"
    log_warn "Add /usr/lib/x86_64-linux-gnu to LD_LIBRARY_PATH if needed"
  fi
  
  return 0
}


