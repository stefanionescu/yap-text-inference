#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Installation Utilities
# =============================================================================
# Functions for installing TensorRT-LLM and its dependencies.
# Follows the pattern from trtllm-example/custom/setup/install-dependencies.sh

_TRT_INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../lib/deps/pip.sh
source "${_TRT_INSTALL_DIR}/../../lib/deps/pip.sh"

# =============================================================================
# CONFIGURATION
# =============================================================================
# TRT-LLM 1.2.0rc5 requires CUDA 13.0, torch 2.9.0, and Python 3.10
# PyTorch version is pinned to torch==2.9.0+cu130 (TRT-LLM requires <=2.9.0)
#
# IMPORTANT: Python 3.11/3.12 do NOT work reliably with TRT-LLM 1.2.0rc5!
# See ADVANCED.md for details on known issues.

# Centralized TRT-LLM version - THIS IS THE SINGLE SOURCE OF TRUTH
TRT_VERSION="${TRT_VERSION:-1.2.0rc5}"

# Derived configurations
TRT_PIP_SPEC="${TRT_PIP_SPEC:-tensorrt_llm==${TRT_VERSION}}"
TRT_EXTRA_INDEX_URL="${TRT_EXTRA_INDEX_URL:-https://pypi.nvidia.com}"

# TRT-LLM repository configuration
TRT_REPO_URL="${TRT_REPO_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}"
TRT_REPO_TAG="${TRT_REPO_TAG:-v${TRT_VERSION}}"
TRT_REPO_DIR="${TRT_REPO_DIR:-${ROOT_DIR:-.}/.trtllm-repo}"
TRT_CLONE_DEPTH="${TRT_CLONE_DEPTH:-1}"
TRT_CLONE_FILTER="${TRT_CLONE_FILTER:-blob:none}"
TRT_CLONE_ATTEMPTS="${TRT_CLONE_ATTEMPTS:-5}"
TRT_CLONE_BACKOFF_SECONDS="${TRT_CLONE_BACKOFF_SECONDS:-2}"

# =============================================================================
# SUPPRESS GIT TRACE LOGGING
# =============================================================================
# Disable git's verbose curl/trace logging globally for this script.
# This affects both direct git commands AND pip's internal git operations
# (e.g. when pip installs packages from git URLs like python-etcd3).
unset GIT_TRACE GIT_CURL_VERBOSE GIT_TRACE_CURL GIT_TRACE_PACKET GIT_TRACE_PERFORMANCE GIT_TRACE_SETUP
export GIT_CURL_VERBOSE=0 GIT_TRACE=0 GIT_TRACE_CURL=0

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
      log_err "[trt] ✗ CUDA_HOME is not set. Install CUDA Toolkit 13.x and export CUDA_HOME."
      return 1
    fi
  fi
  
  if [ ! -d "${CUDA_HOME}/lib64" ]; then
    log_err "[trt] ✗ CUDA_HOME/lib64 not found: ${CUDA_HOME}/lib64"
    return 1
  fi
  
  # Check for CUDA 13 libraries (required by TRT-LLM 1.2.0rc5)
  if ! find "${CUDA_HOME}/lib64" -maxdepth 1 -name "libcublasLt.so.13*" 2>/dev/null | grep -q '.'; then
    if ! ldconfig -p 2>/dev/null | grep -q "libcublasLt.so.13"; then
      log_warn "[trt] ⚠ libcublasLt.so.13 not found - TensorRT-LLM 1.2.0rc5 requires CUDA 13.x runtime libraries"
    fi
  fi
  
  # Ensure CUDA libs are in LD_LIBRARY_PATH
  case ":${LD_LIBRARY_PATH:-}:" in
    *":${CUDA_HOME}/lib64:"*) ;;
    *) export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}" ;;
  esac
  
  return 0
}

# =============================================================================
# PYTORCH INSTALLATION
# =============================================================================

# Install PyTorch and TorchVision with matching CUDA versions
# MUST be done BEFORE TensorRT-LLM to prevent version conflicts
trt_install_pytorch() {
  local torch_version="${TRT_PYTORCH_VERSION:-2.9.0+cu130}"
  local torchvision_version="${TRT_TORCHVISION_VERSION:-0.24.0+cu130}"
  local torch_idx="${TRT_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
  
  log_section "[trt] Installing PyTorch..."
  
  # Install torch and torchvision together from the SAME index to ensure CUDA version match
  local pip_cmd=(
    install --no-cache-dir
    --index-url "${torch_idx}"
    "torch==${torch_version}"
    "torchvision==${torchvision_version}"
  )
  
  _trt_pip_install_with_retry "${pip_cmd[@]}" || {
    log_err "[trt] ✗ Failed to install PyTorch"
    return 1
  }
  
  return 0
}

# Persist torch/torchvision pins so downstream pip installs cannot swap CUDA builds
trt_write_torch_constraints_file() {
  local constraints_file="${TRT_TORCH_CONSTRAINTS_FILE:-${ROOT_DIR:-.}/.run/trt_torch_constraints.txt}"
  local torch_version="${TRT_PYTORCH_VERSION:-2.9.0+cu130}"
  local torchvision_version="${TRT_TORCHVISION_VERSION:-0.24.0+cu130}"

  mkdir -p "$(dirname "${constraints_file}")"
  cat >"${constraints_file}" <<EOF
torch==${torch_version}
torchvision==${torchvision_version}
EOF

  echo "${constraints_file}"
}

# =============================================================================
# TRT-LLM INSTALLATION
# =============================================================================

# pip install with retry
# Uses venv pip (via PATH after activation)
_trt_pip_install_with_retry() {
  local max_attempts="${PIP_INSTALL_ATTEMPTS:-5}"
  local delay="${PIP_INSTALL_BACKOFF_SECONDS:-2}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    if pip_quiet "$@"; then
      return 0
    fi
    attempt=$((attempt + 1))
    if [ "${attempt}" -le "${max_attempts}" ]; then
      log_warn "[trt] ⚠ pip attempt failed; retrying after ${delay}s..."
      sleep "${delay}"
      delay=$((delay * 2))
    fi
  done

  log_err "[trt] ✗ pip command failed after ${max_attempts} attempts"
  return 1
}

# Install TensorRT-LLM from NVIDIA PyPI
trt_install_tensorrt_llm() {
  local nvidia_index="${TRT_EXTRA_INDEX_URL}"
  local target="${TRT_PIP_SPEC}"
  local trt_no_deps="${TRTLLM_NO_DEPS:-0}"
  local torch_idx="${TRT_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
  local constraints_file
  constraints_file=$(trt_write_torch_constraints_file) || {
    log_err "[trt] ✗ Unable to materialize torch constraints"
    return 1
  }
  
  log_info "[trt] Installing the TRT wheel..."
  
  # NOTE: Do NOT use --upgrade here - it can replace torch with a different CUDA version
  # from NVIDIA's index, causing CUDA version mismatch between torch and torchvision
  # Use NVIDIA index as PRIMARY to get real wheels directly (avoid PyPI stub issues)
  local pip_cmd=(
    install --no-cache-dir --timeout 120 --retries 20
    --index-url "${nvidia_index}"
    --extra-index-url "https://pypi.org/simple"
    --extra-index-url "${torch_idx}"
  )
  if [ "${trt_no_deps}" = "1" ]; then
    pip_cmd+=(--no-deps)
  fi
  if [ -n "${constraints_file}" ] && [ -f "${constraints_file}" ]; then
    pip_cmd+=(--constraint "${constraints_file}")
  fi
  pip_cmd+=("${target}")
  
  _trt_pip_install_with_retry "${pip_cmd[@]}" || {
    log_err "[trt] ✗ Failed to install the TRT wheel"
    return 1
  }
  
  return 0
}

# =============================================================================
# VALIDATION
# =============================================================================

# Validate Python shared library
trt_validate_python_libraries() {
  log_info "[trt] Checking Python shared library..."
  local python_root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  if ! PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
      python -W ignore::RuntimeWarning -m src.scripts.trt.validation python-libs; then
    return 1
  fi
}

# Validate CUDA runtime
trt_validate_cuda_runtime() {
  log_info "[trt] Checking CUDA Python bindings..."
  local python_root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  if ! PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
      python -W ignore::RuntimeWarning -m src.scripts.trt.validation cuda-runtime 2>&1; then
    log_err "[trt] ✗ CUDA Python bindings not working"
    log_err "[trt] ✗ Hint: Ensure cuda-python>=13.0 and that CUDA_HOME/lib64 contains CUDA 13 runtime libraries"
    return 1
  fi
  log_info "[trt] ✓ CUDA bindings OK"
  return 0
}

# Validate MPI runtime
trt_validate_mpi_runtime() {
  local need_mpi="${NEED_MPI:-0}"

  if [ "$need_mpi" = "1" ]; then
    log_info "[trt] Checking MPI runtime..."
    local python_root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
    PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
      python -W ignore::RuntimeWarning -m src.scripts.trt.validation mpi
  else
    log_info "[trt] Skipping MPI check (NEED_MPI=0)"
  fi
}

# Validate TensorRT-LLM installation
trt_validate_installation() {
  log_blank
  log_info "[trt] Validating TRT wheel installation..."

  # Check TensorRT-LLM version
  local python_root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  local trt_output
  trt_output=$(PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python -W ignore::RuntimeWarning -m src.scripts.trt.validation trt-install 2>&1) || {
    log_err "[trt] ✗ TensorRT-LLM not installed or not importable"
    echo "${trt_output}" >&2
    return 1
  }
  if [[ "${trt_output}" == *"MODELOPT_MISSING"* ]]; then
    log_warn "[trt] ⚠ TensorRT-LLM import reported: ${trt_output} (ignored for modelopt)"
  else
    log_info "${trt_output}"
  fi
  
  # Validate Python libraries
  trt_validate_python_libraries || return 1
  
  # Validate CUDA runtime
  trt_validate_cuda_runtime || return 1
  
  # Validate MPI if needed
  trt_validate_mpi_runtime || return 1
  
  # Check trtllm-build command
  if ! command -v trtllm-build >/dev/null 2>&1; then
    log_warn "[trt] ⚠ trtllm-build command not found in PATH"
  fi
  
  log_blank
  return 0
}

# =============================================================================
# TRT-LLM REPOSITORY
# =============================================================================

# Clone or update TensorRT-LLM repository for quantization scripts
# Follows the pattern from trtllm-example/custom/build/steps/step_prepare_trtllm_repo.sh
#
# IMPORTANT: We ALWAYS clone a SPECIFIC VERSION TAG (TRT_REPO_TAG) that matches
# TRT_VERSION. The tag contains the correct quantization/requirements.txt for
# that version. Quantization requirements are installed in trt_install_quant_requirements().
trt_prepare_repo() {
  local repo_url="${TRT_REPO_URL}"
  local repo_dir="${TRT_REPO_DIR}"
  local tag_name="${TRT_REPO_TAG}"
  local tag_ref="refs/tags/${tag_name}"
  local clone_depth="${TRT_CLONE_DEPTH}"
  local clone_filter="${TRT_CLONE_FILTER}"
  local clone_attempts="${TRT_CLONE_ATTEMPTS}"
  local clone_delay="${TRT_CLONE_BACKOFF_SECONDS}"
  
  # Clone if not present, reuse if exists
  # Note: FORCE_REBUILD only affects engine/checkpoint builds, not the repo clone
  if [ -d "${repo_dir}" ]; then
    log_info "[trt] Reusing existing TensorRT-LLM repository..."
  else
    log_info "[trt] Cloning TRTLLM repo..."
    
    # Build clone options (--quiet suppresses progress, -c advice.detachedHead=false suppresses detached HEAD warning)
    local clone_opts=("--quiet" "--single-branch" "--no-tags" "--branch" "${tag_name}")
    if [ "${clone_depth}" != "full" ]; then
      clone_opts+=("--depth" "${clone_depth}")
      if [ -n "${clone_filter}" ] && [ "${clone_filter}" != "none" ]; then
        clone_opts+=("--filter=${clone_filter}")
      fi
    fi
    
    # Clone with retry (quiet mode, redirect git noise to /dev/null)
    local attempt=1
    local clone_done=false
    while [ "${attempt}" -le "${clone_attempts}" ]; do
      if git -c http.lowSpeedLimit=0 -c http.lowSpeedTime=999999 -c advice.detachedHead=false clone "${clone_opts[@]}" "${repo_url}" "${repo_dir}" >/dev/null 2>&1; then
        clone_done=true
        break
      fi
      rm -rf "${repo_dir}"
      attempt=$((attempt + 1))
      if [ "${attempt}" -le "${clone_attempts}" ]; then
        sleep "${clone_delay}"
        clone_delay=$((clone_delay * 2))
      fi
    done
    
    if [ "${clone_done}" != "true" ]; then
      log_err "[trt] ✗ Failed to clone TensorRT-LLM repository after ${clone_attempts} attempts"
      return 1
    fi
  fi
  
  # Ensure we're on the correct tag (all git ops quiet)
  if git -C "${repo_dir}" show-ref --verify --quiet "${tag_ref}" >/dev/null 2>&1; then
    : # Tag already present
  else
    log_info "[trt] Fetching ${tag_ref}"
    if [ "${clone_depth}" != "full" ]; then
      git -C "${repo_dir}" fetch --quiet --depth "${clone_depth}" --force origin "${tag_ref}:${tag_ref}" >/dev/null 2>&1 || {
        log_err "[trt] ✗ Unable to fetch ${tag_ref}"
        return 1
      }
    else
      git -C "${repo_dir}" fetch --quiet --force origin "${tag_ref}:${tag_ref}" >/dev/null 2>&1 || {
        log_err "[trt] ✗ Unable to fetch ${tag_ref}"
        return 1
      }
    fi
  fi

  if ! git -c advice.detachedHead=false -C "${repo_dir}" checkout --quiet "${tag_name}" >/dev/null 2>&1; then
    log_err "[trt] ✗ Could not checkout version ${TRT_VERSION} (tag ${tag_name})"
    log_err "[trt] ✗ Hint: ensure ${tag_name} exists in ${repo_url}"
    return 1
  fi
  
  # Verify quantization examples directory exists
  if [ ! -d "${repo_dir}/examples/quantization" ]; then
    log_err "[trt] ✗ Quantization examples not found in ${repo_dir}/examples/quantization"
    ls -la "${repo_dir}/examples/" >&2
    return 1
  fi
  
  export TRT_REPO_DIR="${repo_dir}"
  return 0
}

# Install quantization requirements from the TRT-LLM repository
# This should be called during the quantization step, not during initial install.
# Follows the pattern from trtllm-example/custom/build/steps/step_quantize.sh
# Uses a marker file to skip redundant installs on restart.
trt_install_quant_requirements() {
  local repo_dir="${TRT_REPO_DIR:-${ROOT_DIR:-.}/.trtllm-repo}"
  local quant_reqs="${repo_dir}/examples/quantization/requirements.txt"
  local constraints_file="${repo_dir}/examples/constraints.txt"
  local marker_file="${ROOT_DIR:-.}/.run/trt_quant_deps_installed"
  local filtered_reqs="${ROOT_DIR:-.}/.run/quant_reqs.filtered.txt"
  
  # Skip if already installed (marker present and requirements.txt unchanged)
  if [ -f "${marker_file}" ]; then
    local marker_hash stored_hash
    if [ -f "${quant_reqs}" ]; then
      marker_hash=$(md5sum "${quant_reqs}" 2>/dev/null | awk '{print $1}')
      stored_hash=$(cat "${marker_file}" 2>/dev/null)
      if [ "${marker_hash}" = "${stored_hash}" ]; then
        log_info "[trt] Quantization dependencies already installed, skipping"
        return 0
      fi
    fi
  fi
  
  if [ -f "${quant_reqs}" ]; then
    log_info "[trt] Installing TRT-LLM quantization requirements..."

    # Ensure .run directory exists for filtered requirements file
    mkdir -p "$(dirname "${filtered_reqs}")"

    # Filter out torch/torchvision, CUDA runtime pins, and relative constraint includes.
    # We already install torch/torchvision via trt_install_pytorch.
    awk '
      BEGIN { IGNORECASE = 1 }
      /^(torch==|torchvision==|nvidia-cuda-runtime|nvidia-cudnn|nvidia-cublas|nvidia-cusparse|nvidia-cusolver|nvidia-cufft|nvidia-curand|nvidia-nvjitlink|nvidia-nvtx|cuda-toolkit)/ { next }
      /^[[:space:]]*-c[[:space:]]+\.\.\/constraints\.txt/ { next }
      { print }
    ' "${quant_reqs}" > "${filtered_reqs}" || cp "${quant_reqs}" "${filtered_reqs}"

    local pip_args=(install -r "${filtered_reqs}")
    if [ -f "${constraints_file}" ]; then
      pip_args+=(-c "${constraints_file}")
    else
      log_warn "[trt] ⚠ Constraints file not found at ${constraints_file}; continuing without it"
    fi

    if ! pip_quiet "${pip_args[@]}"; then
      log_warn "[trt] ⚠ Some quantization requirements failed to install"
    fi
    # Upgrade urllib3 to fix GHSA-gm62-xv2j-4w53 and GHSA-2xpw-w6gg-jr37
    pip_quiet install 'urllib3>=2.6.0' || true
    
    # Mark as installed (store hash of requirements.txt)
    mkdir -p "$(dirname "${marker_file}")"
    md5sum "${quant_reqs}" 2>/dev/null | awk '{print $1}' > "${marker_file}"
    log_info "[trt] ✓ Quantization dependencies installed"
    log_blank
  else
    log_warn "[trt] ⚠ Quantization requirements.txt not found at ${quant_reqs}, continuing"
  fi
}
