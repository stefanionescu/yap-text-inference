#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Installation Utilities
# =============================================================================
# Functions for installing TensorRT-LLM and its dependencies.

# =============================================================================
# PREREQUISITES
# =============================================================================

# Ensure CUDA_HOME is set and valid
trt_ensure_cuda_home() {
  if [ -z "${CUDA_HOME:-}" ]; then
    # Try common locations
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

# Install PyTorch with CUDA support for TRT-LLM
trt_install_pytorch() {
  local torch_version="${TRT_PYTORCH_VERSION:-2.9.1+cu130}"
  local torch_idx="${TRT_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
  
  log_info "Installing PyTorch ${torch_version} from ${torch_idx}"
  
  pip install --index-url "${torch_idx}" \
    "torch==${torch_version}" \
    "torchvision" || {
    log_err "Failed to install PyTorch"
    return 1
  }
  
  return 0
}

# =============================================================================
# TRT-LLM INSTALLATION
# =============================================================================

# Install TensorRT-LLM from NVIDIA PyPI
trt_install_tensorrt_llm() {
  local trt_spec="${TRT_PIP_SPEC:-tensorrt_llm}"
  local nvidia_index="${TRT_EXTRA_INDEX_URL:-https://pypi.nvidia.com}"
  
  log_info "Installing TensorRT-LLM: ${trt_spec}"
  
  # Use NVIDIA index as PRIMARY to get real wheels directly
  pip install --no-cache-dir --timeout 120 --retries 20 \
    --index-url "${nvidia_index}" \
    --extra-index-url "https://pypi.org/simple" \
    "${trt_spec}" || {
    log_err "Failed to install TensorRT-LLM"
    return 1
  }
  
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
# VALIDATION
# =============================================================================

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
  
  # Check CUDA bindings
  if ! python - <<'EOF'
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
  then
    log_err "CUDA Python bindings not working"
    return 1
  fi
  
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
# FULL INSTALLATION
# =============================================================================

# Complete TRT-LLM installation sequence
trt_full_install() {
  log_info "Starting TensorRT-LLM full installation..."
  
  # 1. Ensure CUDA is available
  trt_ensure_cuda_home || return 1
  
  # 2. Check CUDA compatibility
  trt_check_cuda_compatibility || {
    log_warn "CUDA version may not be compatible, proceeding anyway"
  }
  
  # 3. Install PyTorch
  trt_install_pytorch || return 1
  
  # 4. Install TensorRT-LLM
  trt_install_tensorrt_llm || return 1
  
  # 5. Prepare repository for quantization
  trt_prepare_repo || return 1
  
  # 6. Validate installation
  trt_validate_installation || return 1
  
  log_info "✓ TensorRT-LLM installation complete"
  return 0
}

