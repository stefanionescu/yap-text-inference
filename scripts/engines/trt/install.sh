#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Installation Utilities
# =============================================================================
# Functions for installing TensorRT-LLM and its dependencies.

# =============================================================================
# CONFIGURATION
# =============================================================================

# TRT-LLM 1.2.0rc5 requires CUDA 13.0 and torch 2.9.x
TRT_PYTORCH_VERSION="${TRT_PYTORCH_VERSION:-2.9.1+cu130}"
TRT_TORCHVISION_VERSION="${TRT_TORCHVISION_VERSION:-0.24.1+cu130}"
TRT_PYTORCH_INDEX_URL="${TRT_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
TRT_PIP_SPEC="${TRT_PIP_SPEC:-tensorrt_llm==1.2.0rc5}"
TRT_EXTRA_INDEX_URL="${TRT_EXTRA_INDEX_URL:-https://pypi.nvidia.com}"

# =============================================================================
# CUDA ENVIRONMENT
# =============================================================================

# Ensure CUDA_HOME is set and valid
trt_ensure_cuda_home() {
  if [ -z "${CUDA_HOME:-}" ]; then
    if [ -d "/usr/local/cuda" ]; then
      export CUDA_HOME="/usr/local/cuda"
    elif [ -d "/usr/local/cuda-13.0" ]; then
      export CUDA_HOME="/usr/local/cuda-13.0"
    else
      log_err "CUDA_HOME is not set. Install CUDA Toolkit 13.x and export CUDA_HOME."
      return 1
    fi
  fi
  
  if [ ! -d "${CUDA_HOME}/lib64" ]; then
    log_err "CUDA_HOME/lib64 not found: ${CUDA_HOME}/lib64"
    return 1
  fi
  
  # Check for CUDA 13 libraries (required by TRT-LLM 1.2.0rc5)
  if ! find "${CUDA_HOME}/lib64" -maxdepth 1 -name "libcublasLt.so.13*" 2>/dev/null | grep -q '.'; then
    if ! ldconfig -p 2>/dev/null | grep -q "libcublasLt.so.13"; then
      log_warn "libcublasLt.so.13 not found - TensorRT-LLM 1.2.0rc5 requires CUDA 13.x runtime libraries"
    fi
  fi
  
  # Ensure CUDA libs are in LD_LIBRARY_PATH
  case ":${LD_LIBRARY_PATH:-}:" in
    *":${CUDA_HOME}/lib64:"*) ;;
    *) export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}" ;;
  esac
  
  log_info "CUDA_HOME: ${CUDA_HOME}"
  return 0
}

# =============================================================================
# PYTORCH INSTALLATION
# =============================================================================

trt_install_pytorch() {
  local torch_version="${TRT_PYTORCH_VERSION}"
  local torchvision_version="${TRT_TORCHVISION_VERSION}"
  local torch_idx="${TRT_PYTORCH_INDEX_URL}"
  
  log_info "Installing PyTorch ${torch_version} + torchvision ${torchvision_version} from ${torch_idx}"
  
  local pkgs=("torch==${torch_version}")
  if [ -n "${torchvision_version}" ]; then
    pkgs+=("torchvision==${torchvision_version}")
  fi
  
  pip install --index-url "${torch_idx}" "${pkgs[@]}" || {
    log_err "Failed to install PyTorch"
    return 1
  }
  
  return 0
}

# =============================================================================
# TRT-LLM INSTALLATION
# =============================================================================

# pip install with retry
_trt_pip_install_with_retry() {
  local max_attempts="${PIP_INSTALL_ATTEMPTS:-5}"
  local delay="${PIP_INSTALL_BACKOFF_SECONDS:-2}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    log_info "pip attempt ${attempt}/${max_attempts}: $*"
    if pip "$@"; then
      return 0
    fi
    attempt=$((attempt + 1))
    if [ "${attempt}" -le "${max_attempts}" ]; then
      log_warn "pip attempt failed; retrying after ${delay}s..."
      sleep "${delay}"
      delay=$((delay * 2))
    fi
  done

  log_err "pip command failed after ${max_attempts} attempts"
  return 1
}

# Install TensorRT-LLM from NVIDIA PyPI
trt_install_tensorrt_llm() {
  local nvidia_index="${TRT_EXTRA_INDEX_URL}"
  local target="${TRT_PIP_SPEC}"
  
  log_info "Installing TensorRT-LLM: ${target}"
  
  # NOTE: Do NOT use --upgrade here - it can replace torch with a different CUDA version
  # from NVIDIA's index, causing CUDA version mismatch between torch and torchvision
  # Use NVIDIA index as PRIMARY to get real wheels directly (avoid PyPI stub issues)
  local pip_cmd=(
    install --no-cache-dir --timeout 120 --retries 20
    --index-url "${nvidia_index}"
    --extra-index-url "https://pypi.org/simple"
    "${target}"
  )
  
  _trt_pip_install_with_retry "${pip_cmd[@]}" || {
    log_err "Failed to install TensorRT-LLM"
    return 1
  }
  
  return 0
}

# =============================================================================
# VALIDATION
# =============================================================================

# Validate Python shared library
trt_validate_python_libraries() {
  log_info "Checking Python shared library..."
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

print("✓ Python shared library OK")
EOF
}

# Validate CUDA runtime
trt_validate_cuda_runtime() {
  log_info "Checking CUDA Python bindings..."
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

print("✓ CUDA runtime OK")
EOF
  ) || true

  if ! echo "$check_output" | grep -q "✓ CUDA runtime OK"; then
    log_err "CUDA Python bindings not working:"
    echo "$check_output" >&2
    log_err "Hint: Ensure cuda-python>=13.0 and that CUDA_HOME/lib64 contains CUDA 13 runtime libraries"
    return 1
  fi

  echo "$check_output"
  return 0
}

# Validate MPI runtime
trt_validate_mpi_runtime() {
  local need_mpi="${NEED_MPI:-0}"

  if [ "$need_mpi" = "1" ]; then
    log_info "Checking MPI runtime..."
    python - <<'EOF'
import sys
try:
    from mpi4py import MPI
    MPI.Get_version()
    print("✓ MPI runtime OK")
except ImportError as exc:
    sys.exit(f"mpi4py not installed: {exc}")
except Exception as exc:
    sys.exit(f"MPI runtime error: {exc}")
EOF
  else
    log_info "Skipping MPI check (NEED_MPI=0)"
  fi
}

# Validate TensorRT-LLM installation
trt_validate_installation() {
  log_info "Validating TensorRT-LLM installation..."
  
  # Check TensorRT-LLM version
  local trt_version
  trt_version=$(python -c "import tensorrt_llm; print(tensorrt_llm.__version__)" 2>/dev/null) || {
    log_err "TensorRT-LLM not installed or not importable"
    return 1
  }
  log_info "TensorRT-LLM version: ${trt_version}"
  
  # Validate Python libraries
  trt_validate_python_libraries || return 1
  
  # Validate CUDA runtime
  trt_validate_cuda_runtime || return 1
  
  # Validate MPI if needed
  trt_validate_mpi_runtime || return 1
  
  # Check trtllm-build command
  if ! command -v trtllm-build >/dev/null 2>&1; then
    log_warn "trtllm-build command not found in PATH"
  else
    log_info "trtllm-build: $(which trtllm-build)"
  fi
  
  log_info "✓ TensorRT-LLM installation validated"
  return 0
}

# =============================================================================
# TRT-LLM REPOSITORY
# =============================================================================

# Clone or update TensorRT-LLM repository for quantization scripts
trt_prepare_repo() {
  local repo_url="${TRT_REPO_URL:-https://github.com/NVIDIA/TensorRT-LLM.git}"
  local repo_branch="${TRT_REPO_BRANCH:-main}"
  local repo_dir="${TRT_REPO_DIR:-${ROOT_DIR:-.}/.trtllm-repo}"
  
  if [ -d "${repo_dir}/.git" ]; then
    log_info "Updating TensorRT-LLM repository at ${repo_dir}"
    (cd "${repo_dir}" && git fetch origin && git checkout "${repo_branch}" && git pull origin "${repo_branch}") || {
      log_warn "Failed to update repo, using existing version"
    }
  else
    log_info "Cloning TensorRT-LLM repository to ${repo_dir}"
    rm -rf "${repo_dir}"
    git clone --depth 1 --branch "${repo_branch}" "${repo_url}" "${repo_dir}" || {
      log_err "Failed to clone TensorRT-LLM repository"
      return 1
    }
  fi
  
  # Install quantization requirements
  local quant_reqs="${repo_dir}/examples/quantization/requirements.txt"
  if [ -f "${quant_reqs}" ]; then
    log_info "Installing TRT-LLM quantization requirements"
    pip install -r "${quant_reqs}" || {
      log_warn "Some quantization requirements failed to install"
    }
  fi
  
  export TRT_REPO_DIR="${repo_dir}"
  return 0
}

# =============================================================================
# FULL INSTALLATION
# =============================================================================

# Complete TRT-LLM installation sequence
# Order: PyTorch -> requirements.txt -> TensorRT-LLM -> validate
trt_full_install() {
  log_info "Starting TensorRT-LLM full installation..."
  
  # 1. Ensure CUDA is available
  trt_ensure_cuda_home || return 1
  
  # 2. Install PyTorch with CUDA support FIRST
  trt_install_pytorch || return 1
  
  # 3. Install application dependencies (requirements-trt.txt)
  # This is handled by 03_install_deps.sh calling install_requirements_without_flashinfer
  
  # 4. Install TensorRT-LLM LAST
  trt_install_tensorrt_llm || return 1
  
  # 5. Validate installation
  trt_validate_installation || return 1
  
  log_info "✓ TensorRT-LLM installation complete"
  return 0
}
