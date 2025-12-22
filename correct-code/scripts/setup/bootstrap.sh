#!/usr/bin/env bash
# =============================================================================
# System Bootstrap Script
# =============================================================================
# Installs system dependencies required for TensorRT-LLM and TTS server.
# This script handles:
# - CUDA driver verification
# - Python development libraries
# - OpenMPI (runtime libs + bin for mpi4py/nemo-toolkit quantization)
# - Basic system utilities
#
# Dependency Caching:
# - Checks if dependencies are already installed with correct versions
# - Skips installation if all deps present (saves time on restart)
# - Set FORCE_INSTALL_DEPS=1 to force reinstall all dependencies
#
# Usage: bash scripts/setup/bootstrap.sh
# Environment: Requires HF_TOKEN to be set
# =============================================================================

set -euo pipefail

# Load common utilities and environment
source "scripts/lib/common.sh"
source "scripts/lib/deps.sh"
load_env_if_present
load_environment

echo ""
echo "[bootstrap] System Bootstrap"

# Check for force install flag
FORCE_INSTALL_DEPS="${FORCE_INSTALL_DEPS:-0}"
if [[ "$FORCE_INSTALL_DEPS" == "1" ]]; then
  echo "[bootstrap] Force install requested - will reinstall all system dependencies"
fi

# =============================================================================
# Helper Functions
# =============================================================================

_check_system_libraries() {
  echo "[bootstrap] Verifying system libraries..."

  # Check Python shared library
  if ! ldconfig -p 2>/dev/null | grep -q "libpython${PYTHON_VERSION}.so"; then
    echo "WARNING: libpython${PYTHON_VERSION}.so not found in library path" >&2
    echo "  Install python3-dev or add library path to LD_LIBRARY_PATH" >&2
  fi
}

# =============================================================================
# CUDA Environment Check
# =============================================================================

echo "[bootstrap] Checking CUDA environment..."
if ! command -v nvidia-smi >/dev/null; then
  echo "ERROR: nvidia-smi not found. Please install NVIDIA drivers first." >&2
  exit 1
fi

if ! assert_cuda13_driver "bootstrap"; then
  echo "[bootstrap] CUDA validation failed; aborting." >&2
  exit 1
fi

CUDA_VER=$(detect_cuda_version)
echo "[bootstrap] Detected CUDA version: ${CUDA_VER:-unknown}"

# =============================================================================
# Python Environment Check
# =============================================================================

echo "[bootstrap] Checking Python environment..."
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"

if ! command -v "python${PYTHON_VERSION}" >/dev/null 2>&1; then
  echo "[bootstrap] python${PYTHON_VERSION} not found."
  echo "[bootstrap] This is expected on managed container images"
else
  echo "[bootstrap] Found python${PYTHON_VERSION}"
fi

# =============================================================================
# System Dependencies Installation
# =============================================================================

if command -v apt-get >/dev/null 2>&1; then
  if [ "${SKIP_APT:-0}" = "1" ]; then
    echo "[bootstrap] SKIP_APT=1 → skipping system package installation"
  else
    echo "[bootstrap] Checking existing system dependencies..."
    
    # Track what needs to be installed - each category independently
    PKGS_TO_INSTALL=()
    NEEDS_APT_UPDATE=0
    
    # Select correct MPI runtime package name (t64 on Ubuntu 24.04+, non-t64 otherwise)
    MPI_PKG="libopenmpi3"
    if apt-cache policy libopenmpi3t64 >/dev/null 2>&1; then
      if apt-cache policy libopenmpi3t64 | grep -q "Candidate:"; then
        MPI_PKG="libopenmpi3t64"
      fi
    fi
    MPI_VER_ARG=""
    if [ -n "${MPI_VERSION_PIN:-}" ]; then
      MPI_VER_ARG="=${MPI_VERSION_PIN}"
    fi
    
    # ---------------------------------------------------------------------------
    # Check system utilities (git, wget, curl, jq)
    # ---------------------------------------------------------------------------
    MISSING_UTILS=()
    for util in git wget curl jq; do
      if [[ "$FORCE_INSTALL_DEPS" == "1" ]] || ! command -v "$util" >/dev/null 2>&1; then
        MISSING_UTILS+=("$util")
      fi
    done
    
    if [[ ${#MISSING_UTILS[@]} -gt 0 ]]; then
      echo "[bootstrap] Missing utilities: ${MISSING_UTILS[*]}"
      PKGS_TO_INSTALL+=("${MISSING_UTILS[@]}")
      NEEDS_APT_UPDATE=1
    else
      echo "[bootstrap] System utilities OK: git, wget, curl, jq"
    fi
    
    # ---------------------------------------------------------------------------
    # Check Python dev packages
    # ---------------------------------------------------------------------------
    MISSING_PYTHON_PKGS=()
    for pkg in "python${PYTHON_VERSION}-venv" "python${PYTHON_VERSION}-dev"; do
      if [[ "$FORCE_INSTALL_DEPS" == "1" ]] || ! is_apt_pkg_installed "$pkg"; then
        MISSING_PYTHON_PKGS+=("$pkg")
      fi
    done
    
    if [[ ${#MISSING_PYTHON_PKGS[@]} -gt 0 ]]; then
      echo "[bootstrap] Missing Python packages: ${MISSING_PYTHON_PKGS[*]}"
      PKGS_TO_INSTALL+=("${MISSING_PYTHON_PKGS[@]}")
      NEEDS_APT_UPDATE=1
    else
      echo "[bootstrap] Python dev packages OK"
    fi
    
    # ---------------------------------------------------------------------------
    # Check MPI dependencies
    # ---------------------------------------------------------------------------
    MISSING_MPI_PKGS=()
    MPI_PACKAGES=("$MPI_PKG" "openmpi-bin" "openmpi-common")
    
    for pkg in "${MPI_PACKAGES[@]}"; do
      if [[ "$FORCE_INSTALL_DEPS" == "1" ]]; then
        MISSING_MPI_PKGS+=("${pkg}${MPI_VER_ARG}")
      elif ! is_apt_pkg_installed "$pkg"; then
        echo "[bootstrap] MPI package '$pkg' is NOT installed"
        MISSING_MPI_PKGS+=("${pkg}${MPI_VER_ARG}")
      elif [[ -n "$MPI_VER_ARG" ]]; then
        # Check version if pinned
        installed_ver=$(get_apt_pkg_version "$pkg")
        required_prefix="${MPI_VERSION_PIN%%-*}"
        installed_prefix="${installed_ver%%-*}"
        if [[ "$installed_prefix" != "$required_prefix" ]]; then
          echo "[bootstrap] MPI package '$pkg' version mismatch: $installed_ver (need $MPI_VERSION_PIN)"
          MISSING_MPI_PKGS+=("${pkg}${MPI_VER_ARG}")
        fi
      fi
    done
    
    if [[ ${#MISSING_MPI_PKGS[@]} -gt 0 ]]; then
      echo "[bootstrap] Missing/outdated MPI packages: ${MISSING_MPI_PKGS[*]}"
      PKGS_TO_INSTALL+=("${MISSING_MPI_PKGS[@]}")
      NEEDS_APT_UPDATE=1
    else
      echo "[bootstrap] MPI packages OK"
    fi
    
    # ---------------------------------------------------------------------------
    # Install only what's missing
    # ---------------------------------------------------------------------------
    if [[ ${#PKGS_TO_INSTALL[@]} -eq 0 ]]; then
      echo "[bootstrap] All system dependencies already installed - skipping apt install"
    else
      echo "[bootstrap] Installing missing packages: ${PKGS_TO_INSTALL[*]}"
      
      # Only update if we actually need to install something
      if [[ "$NEEDS_APT_UPDATE" == "1" ]]; then
        apt-get update -y || {
          echo "WARNING: apt-get update failed, continuing anyway" >&2
        }
      fi
      
      # Install only the missing packages
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-upgrade --no-install-recommends \
        "${PKGS_TO_INSTALL[@]}" || {
        echo "WARNING: Some packages failed to install, continuing anyway" >&2
      }
      
      # Hold MPI packages to prevent drift (only if we installed them)
      if [[ ${#MISSING_MPI_PKGS[@]} -gt 0 ]]; then
        apt-mark hold "$MPI_PKG" openmpi-bin openmpi-common >/dev/null 2>&1 || true
      fi
    fi
    
    # Verify critical libraries are available
    _check_system_libraries
  fi
else
  echo "[bootstrap] apt-get not available, skipping system package installation"
  echo "[bootstrap] Ensure the following are installed manually:"
  echo "  - Python ${PYTHON_VERSION} with development headers"
  echo "  - Basic build tools (git, wget, curl)"
fi

# =============================================================================
# Environment Validation
# =============================================================================

echo "[bootstrap] Validating environment..."

# Check HF token
require_env HF_TOKEN

echo "[bootstrap] System bootstrap completed successfully"
