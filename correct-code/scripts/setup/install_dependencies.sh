#!/usr/bin/env bash
# =============================================================================
# Python Dependencies Installation Script
# =============================================================================
# Creates Python virtual environment and installs all required dependencies:
# - PyTorch with appropriate CUDA support
# - TensorRT-LLM from NVIDIA PyPI
# - All Python package dependencies
# - Validates critical runtime libraries
#
# Dependency Caching:
# - Checks if venv exists and is valid before creating
# - Checks if PyTorch/TensorRT-LLM are installed with correct versions
# - Skips installation if all deps present with correct versions
# - Uninstalls wrong versions before installing correct ones
# - Set FORCE_INSTALL_DEPS=1 to force reinstall everything
#
# Usage: bash scripts/setup/install_dependencies.sh
# Environment: Requires HF_TOKEN, optionally PYTHON_VERSION, VENV_DIR
# =============================================================================

set -euo pipefail

# Load common utilities and environment
source "scripts/lib/common.sh"
source "scripts/lib/deps.sh"
load_env_if_present
load_environment

echo ""
echo "[install] Python Dependencies Installation"

# Check for force install flag
FORCE_INSTALL_DEPS="${FORCE_INSTALL_DEPS:-0}"
if [[ "$FORCE_INSTALL_DEPS" == "1" ]]; then
  echo "[install] Force install requested - will reinstall all Python dependencies"
fi

# =============================================================================
# Helper Functions
# =============================================================================

_ensure_venv_support() {
  local py_exe="$1"
  local py_majmin="$2"

  if ! $py_exe -m ensurepip --version >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "[install] Installing Python venv support..."
      apt-get update -y || true
      DEBIAN_FRONTEND=noninteractive apt-get install -y \
        "python${py_majmin}-venv" ||
        DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv || true
    else
      echo "WARNING: ensurepip missing and apt-get unavailable. venv creation may fail." >&2
    fi
  fi
}

_bootstrap_pip() {
  # Ensure pip is available
  if ! python -m pip --version >/dev/null 2>&1; then
    python -m ensurepip || true
  fi

  # Install pinned versions - NO --upgrade to avoid breaking version pins
  # setuptools must be <80 for TRT-LLM 1.2.0rc5 compatibility
  python -m pip install --no-cache-dir pip "setuptools<80" wheel || {
    python -m ensurepip || true
    python -m pip install --no-cache-dir pip "setuptools<80" wheel
  }
}

_install_pytorch() {
  local torch_version="${PYTORCH_VERSION:-2.9.0+cu130}"
  local torchvision_version="${TORCHVISION_VERSION:-0.24.0+cu130}"
  local torch_idx="${PYTORCH_INDEX_URL:-}"
  local cuda_ver="${CUDA_VER:-$(detect_cuda_version)}"

  if [ -z "$torch_idx" ]; then
    torch_idx=$(map_torch_index_url "$cuda_ver")
  fi

  echo "[install] Installing PyTorch ${torch_version} (index: $torch_idx)"
  local pkgs=("torch==${torch_version}")
  if [ -n "$torchvision_version" ]; then
    pkgs+=("torchvision==${torchvision_version}")
  fi
  pip install --index-url "$torch_idx" "${pkgs[@]}"
}

_ensure_cuda_home() {
  if [ -z "${CUDA_HOME:-}" ]; then
    echo "[install] ERROR: CUDA_HOME is not set. Install CUDA Toolkit 13.x and export CUDA_HOME before running this script." >&2
    echo "Example: export CUDA_HOME=/usr/local/cuda-13.0" >&2
    exit 1
  fi
  if [ ! -d "${CUDA_HOME}/lib64" ]; then
    echo "[install] ERROR: ${CUDA_HOME}/lib64 not found. Verify your CUDA installation." >&2
    exit 1
  fi
  if ! find "${CUDA_HOME}/lib64" -maxdepth 1 -name "libcublasLt.so.13*" | grep -q '.'; then
    if ! ldconfig -p 2>/dev/null | grep -q "libcublasLt.so.13"; then
      cat >&2 <<'ERR'
[install] ERROR: libcublasLt.so.13 not found in CUDA library path.
TensorRT-LLM 1.2.0rc5 requires CUDA 13.x runtime libraries.
Install the CUDA 13 toolkit and ensure CUDA_HOME points at that installation.
ERR
      exit 1
    fi
  fi
  case ":${LD_LIBRARY_PATH:-}:" in
    *":${CUDA_HOME}/lib64:"*) ;;
    *) export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}" ;;
  esac
}

_pip_install_with_retry() {
  local max_attempts="${PIP_INSTALL_ATTEMPTS:-5}"
  local delay="${PIP_INSTALL_BACKOFF_SECONDS:-2}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    echo "[install] pip attempt ${attempt}/${max_attempts}: $*"
    if pip "$@"; then
      return 0
    fi
    attempt=$((attempt + 1))
    if [ "${attempt}" -le "${max_attempts}" ]; then
      echo "[install] pip attempt failed; retrying after ${delay}s..."
      sleep "${delay}"
      delay=$((delay * 2))
    fi
  done

  echo "[install] ERROR: pip command failed after ${max_attempts} attempts" >&2
  return 1
}

_install_tensorrt_llm() {
  local nvidia_index="${TRTLLM_EXTRA_INDEX_URL:-https://pypi.nvidia.com}"
  local target="${TRTLLM_WHEEL_URL:-${TRTLLM_PIP_SPEC:-tensorrt_llm}}"
  # NOTE: Do NOT use --upgrade here - it can replace torch with a different CUDA version
  # from NVIDIA's index, causing CUDA version mismatch between torch and torchvision
  # Use NVIDIA index as PRIMARY to get real wheels directly (avoid PyPI stub issues)
  local pip_cmd=(
    install --no-cache-dir --timeout 120 --retries 20
    --index-url "$nvidia_index"
    --extra-index-url "https://pypi.org/simple"
    "$target"
  )
  if [ -n "${TENSORRT_PIP_EXTRAS:-}" ]; then
    # shellcheck disable=SC2206
    local extras=(${TENSORRT_PIP_EXTRAS})
    pip_cmd+=("${extras[@]}")
  fi
  _pip_install_with_retry "${pip_cmd[@]}"
}

_validate_python_libraries() {
  echo "[install] Checking Python shared library..."
  python - <<'EOF'
import ctypes
import ctypes.util
import sys

version = f"{sys.version_info.major}.{sys.version_info.minor}"
lib_name = ctypes.util.find_library(f"python{version}")

if not lib_name:
    raise SystemExit(
        "Unable to locate libpython shared library. "
        "Install python3-dev and ensure LD_LIBRARY_PATH includes its directory."
    )

try:
    ctypes.CDLL(lib_name)
except OSError as exc:
    raise SystemExit(f"Found {lib_name} but failed to load it: {exc}")

print("[install] Python shared library OK")
EOF
}

_validate_cuda_runtime() {
  echo "[install] Checking CUDA Python bindings..."
  local check_output
  check_output=$(
    python - <<'EOF'
import sys
from importlib.metadata import PackageNotFoundError, version

try:
    ver = version("cuda-python")
except PackageNotFoundError:
    print("MISSING: cuda-python not installed")
    sys.exit(1)

major = int(ver.split(".", 1)[0])
try:
    if major >= 13:
        from cuda.bindings import runtime as cudart
    else:
        from cuda import cudart
except Exception as exc:
    print(f"IMPORT_ERROR: {type(exc).__name__}: {exc}")
    sys.exit(1)

err, _ = cudart.cudaDriverGetVersion()
if err != 0:
    print(f"CUDART_ERROR: cudaDriverGetVersion -> {err}")
    sys.exit(1)

print("[install] CUDA runtime OK")
EOF
  ) || true

  if ! echo "$check_output" | grep -q "\[install\] CUDA runtime OK"; then
    echo "ERROR: CUDA Python bindings not working:" >&2
    echo "$check_output" >&2
    echo "Hint: Ensure cuda-python>=13.0 and that CUDA_HOME/lib64 contains CUDA 13 runtime libraries" >&2
    exit 1
  fi

  echo "$check_output"
}

_validate_huggingface_auth() {
  echo "[install] Validating HuggingFace authentication..."
  python - <<'EOF'
import os
from huggingface_hub import login

token = os.environ.get("HF_TOKEN")
if not token:
    raise SystemExit("HF_TOKEN not set")

login(token=token, add_to_git_credential=False)
print("[install] HuggingFace authentication OK")
EOF
}

# =============================================================================
# Configuration
# =============================================================================
# Version constants come from scripts/lib/environment.sh (loaded via load_environment)

VENV_DIR="${VENV_DIR:-$PWD/.venv}"
if [ -z "${CUDA_HOME:-}" ] && [ -d "/usr/local/cuda" ]; then
  export CUDA_HOME="/usr/local/cuda"
fi

# Validate environment
require_env HF_TOKEN

# =============================================================================
# Platform Check
# =============================================================================

if ! assert_cuda13_driver "install"; then
  echo "[install] CUDA validation failed; aborting." >&2
  exit 1
fi

if [ "$(uname -s)" != "Linux" ]; then
  echo "[install] TensorRT-LLM requires Linux with NVIDIA GPUs. Skipping installation."
  exit 0
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "WARNING: nvidia-smi not detected. GPU functionality may not work." >&2
fi

echo "[install] Validating CUDA toolkit (expect CUDA 13 libs)..."
_ensure_cuda_home

# =============================================================================
# Python Virtual Environment Setup
# =============================================================================

echo "[install] Setting up Python virtual environment..."

# Find Python executable
PY_EXE=$(choose_python_exe) || {
  echo "ERROR: Python ${PYTHON_VERSION} not found. Please install it first." >&2
  exit 1
}

echo "[install] Using Python: $PY_EXE"
PY_MAJMIN=$($PY_EXE -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[install] Python version: $PY_MAJMIN"

# Check if existing venv is valid and has all correct dependencies
VENV_EXISTS=0
NEEDS_PYTORCH=1
NEEDS_TORCHVISION=1
NEEDS_TRTLLM=1
NEEDS_REQUIREMENTS=1

if [[ "$FORCE_INSTALL_DEPS" != "1" ]] && check_venv_exists "$VENV_DIR"; then
  VENV_EXISTS=1
  echo "[install] Found existing virtual environment at: $VENV_DIR"
  
  # Activate to check installed packages
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  
  # Check PyTorch
  PYTORCH_CHECK_RESULT=0
  check_pytorch_installed "${PYTORCH_VERSION%%+*}" python || PYTORCH_CHECK_RESULT=$?
  if [[ "$PYTORCH_CHECK_RESULT" -eq 0 ]]; then
    NEEDS_PYTORCH=0
  elif [[ "$PYTORCH_CHECK_RESULT" -eq 2 ]]; then
    # Wrong version installed - uninstall it
    echo "[install] Will uninstall wrong PyTorch version and reinstall correct one"
    uninstall_pip_pkg_if_wrong_version "torch" "${PYTORCH_VERSION%%+*}" python
  fi
  
  # Check TorchVision
  TORCHVISION_CHECK_RESULT=0
  check_torchvision_installed "${TORCHVISION_VERSION%%+*}" python || TORCHVISION_CHECK_RESULT=$?
  if [[ "$TORCHVISION_CHECK_RESULT" -eq 0 ]]; then
    NEEDS_TORCHVISION=0
  elif [[ "$TORCHVISION_CHECK_RESULT" -eq 2 ]]; then
    # Wrong version installed - uninstall it
    echo "[install] Will uninstall wrong TorchVision version and reinstall correct one"
    uninstall_pip_pkg_if_wrong_version "torchvision" "${TORCHVISION_VERSION%%+*}" python
  fi
  
  # Check TensorRT-LLM
  TRTLLM_VER="${TRTLLM_PIP_SPEC##*==}"
  TRTLLM_VER="${TRTLLM_VER:-1.2.0rc5}"
  TRTLLM_CHECK_RESULT=0
  check_trtllm_installed "$TRTLLM_VER" python || TRTLLM_CHECK_RESULT=$?
  if [[ "$TRTLLM_CHECK_RESULT" -eq 0 ]]; then
    NEEDS_TRTLLM=0
  elif [[ "$TRTLLM_CHECK_RESULT" -eq 2 ]]; then
    # Wrong version installed - uninstall it
    echo "[install] Will uninstall wrong TensorRT-LLM version and reinstall correct one"
    uninstall_pip_pkg_if_wrong_version "tensorrt_llm" "$TRTLLM_VER" python
  fi
  
  # Check requirements.txt packages - actually check each package version
  REQUIREMENTS_CHECK_RESULT=0
  check_requirements_installed "requirements.txt" python || REQUIREMENTS_CHECK_RESULT=$?
  if [[ "$REQUIREMENTS_CHECK_RESULT" -eq 0 ]]; then
    NEEDS_REQUIREMENTS=0
  elif [[ "$REQUIREMENTS_CHECK_RESULT" -eq 2 ]]; then
    # Some packages have wrong versions - uninstall them first
    echo "[install] Will uninstall wrong version packages from requirements.txt"
    uninstall_wrong_requirements_packages python
  fi
  
  # If all deps are present, skip installation entirely
  if [[ "$NEEDS_PYTORCH" == "0" && "$NEEDS_TORCHVISION" == "0" && "$NEEDS_TRTLLM" == "0" && "$NEEDS_REQUIREMENTS" == "0" ]]; then
    echo "[install] All Python dependencies already installed with correct versions - skipping installation"
    
    # Still run validations
    _validate_python_libraries
    _validate_cuda_runtime
    _validate_huggingface_auth
    
    echo "[install] All dependencies validated successfully"
    exit 0
  fi
  
  echo "[install] Some dependencies need to be installed/updated"
else
  # Create new virtual environment
  # Ensure venv module is available
  _ensure_venv_support "$PY_EXE" "$PY_MAJMIN"

  # Create virtual environment
  echo "[install] Creating virtual environment at: $VENV_DIR"
  $PY_EXE -m venv "$VENV_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

# =============================================================================
# Python Package Installation
# =============================================================================

echo "[install] Upgrading pip and core tools..."
_bootstrap_pip

# Install PyTorch if needed
if [[ "$NEEDS_PYTORCH" == "1" || "$NEEDS_TORCHVISION" == "1" ]]; then
  echo "[install] Installing PyTorch with CUDA support..."
  _install_pytorch
else
  echo "[install] PyTorch already installed with correct version - skipping"
fi

# Install requirements.txt deps if needed
if [[ "$NEEDS_REQUIREMENTS" == "1" ]]; then
  echo "[install] Installing application dependencies..."
  pip install -r requirements.txt
else
  echo "[install] Application dependencies already installed - skipping"
fi

# Install TensorRT-LLM if needed
if [[ "$NEEDS_TRTLLM" == "1" ]]; then
  echo "[install] Installing TensorRT-LLM..."
  _install_tensorrt_llm
else
  echo "[install] TensorRT-LLM already installed with correct version - skipping"
fi

# =============================================================================
# Runtime Validation
# =============================================================================

echo "[install] Validating installation..."
_validate_python_libraries
_validate_cuda_runtime
_validate_huggingface_auth

echo "[install] All dependencies installed successfully"
