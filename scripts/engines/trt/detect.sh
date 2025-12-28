#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Detection Utilities
# =============================================================================
# TRT-specific detection: pre-quantized models, CUDA version checks,
# and pre-built engine discovery from HuggingFace repos.
# GPU detection: use lib/common/gpu_detect.sh functions directly.

_TRT_DETECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common GPU detection
# shellcheck source=../../lib/common/gpu_detect.sh
source "${_TRT_DETECT_DIR}/../../lib/common/gpu_detect.sh"

# =============================================================================
# TRT-LLM VERSION DETECTION
# =============================================================================

# Detect installed TensorRT-LLM version
# Returns version string (e.g., "1.2.0rc5") or "unknown"
trt_detect_trtllm_version() {
  if command -v python >/dev/null 2>&1; then
    local version
    version=$(python -c "import tensorrt_llm; print(tensorrt_llm.__version__)" 2>/dev/null | tail -n1 || echo "")
    if [ -n "${version}" ]; then
      echo "${version}"
      return 0
    fi
  fi
  echo "unknown"
  return 1
}

# Generate current system's engine label
# Format: sm{arch}_trt-llm-{version}_cuda{version}
# Example: sm90_trt-llm-1.2.0rc5_cuda13.0
trt_get_current_engine_label() {
  local sm_arch="${GPU_SM_ARCH:-$(gpu_detect_sm_arch)}"
  local trtllm_ver
  trtllm_ver=$(trt_detect_trtllm_version)
  local cuda_ver
  cuda_ver=$(trt_detect_cuda_version)
  
  if [ -z "${sm_arch}" ] || [ "${trtllm_ver}" = "unknown" ] || [ -z "${cuda_ver}" ]; then
    echo ""
    return 1
  fi
  
  echo "${sm_arch}_trt-llm-${trtllm_ver}_cuda${cuda_ver}"
}

# =============================================================================
# QUANTIZATION SCRIPT
# =============================================================================

# Get the quantization script for a model
# Uses the standard quantize.py for all models (including MoE)
trt_get_quantize_script() {
  local model="${1:-}"
  local trtllm_repo="${2:-${TRT_REPO_DIR}}"
  
  echo "${trtllm_repo}/examples/quantization/quantize.py"
}

# =============================================================================
# TRT PRE-QUANTIZED MODEL DETECTION
# =============================================================================

# Check if model is a TRT pre-quantized model (contains both 'trt' and 'awq')
trt_is_prequantized_model() {
  local model="${1:-}"
  if [ -z "${model}" ]; then
    return 1
  fi
  
  local lowered
  lowered=$(echo "${model}" | tr '[:upper:]' '[:lower:]')
  
  # Must contain both 'trt' and 'awq'
  if echo "${lowered}" | grep -q "trt" && echo "${lowered}" | grep -q "awq"; then
    return 0
  fi
  
  return 1
}

# =============================================================================
# CUDA VERSION DETECTION
# =============================================================================

# Convert version string (e.g., "13.2") to integer (e.g., 1302) for comparison
_trt_version_to_int() {
  local ver="${1:-}"
  if [ -z "$ver" ]; then
    echo "0"
    return 1
  fi
  local major minor
  major=$(echo "$ver" | cut -d. -f1 | grep -oE '[0-9]+' | head -n1)
  minor=$(echo "$ver" | cut -d. -f2 | grep -oE '[0-9]+' | head -n1)
  major="${major:-0}"
  minor="${minor:-0}"
  # Pad minor to 2 digits: 13.2 -> 1302, 13.0 -> 1300
  printf '%d%02d\n' "$major" "$minor"
}

# Detect CUDA toolkit version
trt_detect_cuda_version() {
  # 1. Check CUDA_VERSION env var (common in containers)
  if [ -n "${CUDA_VERSION:-}" ]; then
    echo "${CUDA_VERSION}" | grep -oE '^[0-9]+\.[0-9]+' 2>/dev/null || echo "${CUDA_VERSION}"
    return
  fi
  
  # 2. Check nvcc (actual toolkit version)
  if command -v nvcc >/dev/null 2>&1; then
    nvcc --version 2>/dev/null | grep -oE 'release [0-9]+\.[0-9]+' | awk '{print $2}' 2>/dev/null && return
  fi
  
  # 3. Fallback to nvidia-smi
  if command -v nvidia-smi >/dev/null 2>&1; then
    timeout 10s nvidia-smi 2>/dev/null | grep -o "CUDA Version: [0-9][0-9]*\.[0-9]*" | awk '{print $3}' 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# Check if CUDA version is compatible with TRT-LLM 1.2.0rc5 (requires CUDA 13.0)
trt_check_cuda_compatibility() {
  local cuda_ver
  cuda_ver=$(trt_detect_cuda_version)
  
  if [ -z "${cuda_ver}" ]; then
    log_warn "[cuda] ⚠ Could not detect CUDA version"
    return 1
  fi
  
  local major
  major=$(echo "${cuda_ver}" | cut -d. -f1)
  
  if [ "${major}" -lt 13 ]; then
    log_warn "[cuda] ⚠ TRT-LLM 1.2.0rc5 requires CUDA 13.0+, found ${cuda_ver}"
    return 1
  fi
  
  return 0
}

# Comprehensive CUDA 13.x check: validates BOTH toolkit AND driver
# Checks: 1) toolkit version via nvcc/env, 2) driver capability via cudaDriverGetVersion or nvidia-smi
# Usage: trt_assert_cuda13_driver [prefix]
trt_assert_cuda13_driver() {
  local prefix="${1:-cuda}"
  local min_cuda_int=1300
  local toolkit_ver toolkit_int driver_ver driver_int driver_source

  # -------------------------------------------------------------------------
  # 1. TOOLKIT CHECK: What CUDA toolkit is installed?
  # -------------------------------------------------------------------------
  toolkit_ver=$(trt_detect_cuda_version)
  toolkit_int=$(_trt_version_to_int "$toolkit_ver") || toolkit_int=0

  if [ "$toolkit_int" -eq 0 ]; then
    log_err "[${prefix}] ✗ Could not detect CUDA toolkit version."
    log_err "[${prefix}] ✗ Ensure CUDA 13.x is installed and nvcc is in PATH, or set CUDA_VERSION env var."
    return 1
  fi

  if [ "$toolkit_int" -lt "$min_cuda_int" ]; then
    log_err "[${prefix}] ✗ CUDA toolkit 13.x required. Detected: '${toolkit_ver}' (int=${toolkit_int})"
    log_err "[${prefix}] ✗ Hint: Install CUDA 13 toolkit and ensure nvcc is in PATH."
    return 1
  fi

  # -------------------------------------------------------------------------
  # 2. DRIVER CHECK: Does the GPU driver support CUDA 13?
  # -------------------------------------------------------------------------
  driver_ver=""
  driver_int=0
  driver_source=""

  # Method A: Use cuda-python if available (most accurate - queries actual driver)
  if command -v python >/dev/null 2>&1; then
    local py_driver
    py_driver=$(
      python - <<'PY' 2>/dev/null
try:
    try:
        from cuda.bindings import runtime as cudart
    except Exception:
        from cuda import cudart
    err, ver = cudart.cudaDriverGetVersion()
    if err == 0:
        # ver is e.g. 13020 for CUDA 13.2
        major = ver // 1000
        minor = (ver % 1000) // 10
        print(f"{major}.{minor}")
except Exception:
    pass
PY
    ) || true
    if [ -n "$py_driver" ]; then
      driver_ver="$py_driver"
      driver_source="cuda-python"
    fi
  fi

  # Method B: Fall back to nvidia-smi (shows driver's max supported CUDA)
  if [ -z "$driver_ver" ] && command -v nvidia-smi >/dev/null 2>&1; then
    driver_ver=$(timeout 5s nvidia-smi 2>/dev/null | grep -m1 -o "CUDA Version: [0-9][0-9]*\.[0-9]*" | awk '{print $3}' || true)
    if [ -n "$driver_ver" ]; then
      driver_source="nvidia-smi"
    fi
  fi

  if [ -z "$driver_ver" ]; then
    log_warn "[${prefix}] ⚠ Could not query driver CUDA capability (no cuda-python, nvidia-smi failed)."
    log_warn "[${prefix}] ⚠ Proceeding with toolkit version only - runtime errors may occur if driver is too old."
    return 0
  fi

  driver_int=$(_trt_version_to_int "$driver_ver") || driver_int=0

  if [ "$driver_int" -lt "$min_cuda_int" ]; then
    log_err "[${prefix}] ✗ NVIDIA driver only supports up to CUDA ${driver_ver} (need 13.x+)."
    log_err "[${prefix}] ✗ Source: ${driver_source}"
    log_err "[${prefix}] ✗ Hint: Upgrade to a newer NVIDIA driver that supports CUDA 13.x."
    log_err "[${prefix}] ✗ Your toolkit is CUDA ${toolkit_ver}, but the driver can't run CUDA 13 code."
    return 1
  fi

  return 0
}

# =============================================================================
# PRE-BUILT ENGINE DETECTION FROM HUGGINGFACE
# =============================================================================

# List available engine directories from a HuggingFace TRT repo
# Returns newline-separated list of engine labels (e.g., "sm90_trt-llm-1.2.0rc5_cuda13.0")
# Usage: trt_list_remote_engines <repo_id>
trt_list_remote_engines() {
  local repo_id="${1:-}"
  if [ -z "${repo_id}" ]; then
    return 1
  fi
  
  python -c "
import sys
try:
    from huggingface_hub import list_repo_tree
    items = list(list_repo_tree('${repo_id}', path_in_repo='trt-llm/engines', repo_type='model'))
    for item in items:
        if item.path.startswith('trt-llm/engines/') and item.path.count('/') == 2:
            # Extract engine label from path: trt-llm/engines/{label}
            label = item.path.split('/')[-1]
            print(label)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || true
}

# Parse engine label into components
# Usage: trt_parse_engine_label <label>
# Returns: sm_arch trtllm_version cuda_version (space-separated)
# Example: "sm90_trt-llm-1.2.0rc5_cuda13.0" -> "sm90 1.2.0rc5 13.0"
trt_parse_engine_label() {
  local label="${1:-}"
  if [ -z "${label}" ]; then
    return 1
  fi
  
  # Format: sm{arch}_trt-llm-{version}_cuda{version}
  local sm_arch trtllm_version cuda_version
  
  # Extract SM arch (first part before _trt-llm-)
  sm_arch="${label%%_trt-llm-*}"
  
  # Extract TRT-LLM version (between _trt-llm- and _cuda)
  local rest="${label#*_trt-llm-}"
  trtllm_version="${rest%%_cuda*}"
  
  # Extract CUDA version (after _cuda)
  cuda_version="${rest#*_cuda}"
  
  if [ -z "${sm_arch}" ] || [ -z "${trtllm_version}" ] || [ -z "${cuda_version}" ]; then
    return 1
  fi
  
  echo "${sm_arch} ${trtllm_version} ${cuda_version}"
}

# Check if a remote engine label matches current system
# Usage: trt_engine_matches_system <label>
# Returns: 0 if compatible, 1 if not
trt_engine_matches_system() {
  local label="${1:-}"
  if [ -z "${label}" ]; then
    return 1
  fi
  
  local current_sm="${GPU_SM_ARCH:-$(gpu_detect_sm_arch)}"
  local current_trtllm
  current_trtllm=$(trt_detect_trtllm_version)
  local current_cuda
  current_cuda=$(trt_detect_cuda_version)
  
  # Parse the remote engine label
  local parsed
  parsed=$(trt_parse_engine_label "${label}") || return 1
  read -r remote_sm remote_trtllm remote_cuda <<< "${parsed}"
  
  # Check SM arch match (must be exact - engines are GPU-specific)
  if [ "${remote_sm}" != "${current_sm}" ]; then
    return 1
  fi
  
  # Check TRT-LLM version match (exact match required for ABI compatibility)
  if [ "${remote_trtllm}" != "${current_trtllm}" ]; then
    return 1
  fi
  
  # Check CUDA version match (major.minor must match)
  # Allow for minor differences in patch version (e.g., 13.0 ~= 13.0.1)
  local remote_cuda_major_minor="${remote_cuda%.*}"
  local current_cuda_major_minor="${current_cuda%.*}"
  
  # Handle case where CUDA is just major.minor (no patch)
  if [[ "${remote_cuda}" != *.*.* ]]; then
    remote_cuda_major_minor="${remote_cuda}"
  fi
  if [[ "${current_cuda}" != *.*.* ]]; then
    current_cuda_major_minor="${current_cuda}"
  fi
  
  if [ "${remote_cuda_major_minor}" != "${current_cuda_major_minor}" ]; then
    return 1
  fi
  
  return 0
}

# Find a compatible pre-built engine from a HuggingFace repo
# Usage: trt_find_compatible_engine <repo_id>
# Returns: engine label if found, empty string if none compatible
trt_find_compatible_engine() {
  local repo_id="${1:-}"
  if [ -z "${repo_id}" ]; then
    return 1
  fi
  
  local current_sm="${GPU_SM_ARCH:-$(gpu_detect_sm_arch)}"
  local current_trtllm
  current_trtllm=$(trt_detect_trtllm_version)
  local current_cuda
  current_cuda=$(trt_detect_cuda_version)
  
  log_info "[engine] Checking for pre-built engines in ${repo_id}..."
  log_info "[engine]   Current system: ${current_sm}, TRT-LLM ${current_trtllm}, CUDA ${current_cuda}"
  
  local engines
  engines=$(trt_list_remote_engines "${repo_id}")
  
  if [ -z "${engines}" ]; then
    log_info "[engine]   No pre-built engines found in repository"
    return 1
  fi
  
  local engine
  while IFS= read -r engine; do
    if [ -z "${engine}" ]; then
      continue
    fi
    log_info "[engine]   Checking engine: ${engine}"
    if trt_engine_matches_system "${engine}"; then
      log_info "[engine] ✓ Found compatible engine: ${engine}"
      echo "${engine}"
      return 0
    fi
  done <<< "${engines}"
  
  log_info "[engine]   No compatible pre-built engine found (will build from checkpoint)"
  return 1
}

# Download a pre-built engine from HuggingFace
# Usage: trt_download_prebuilt_engine <repo_id> <engine_label> [target_dir]
# Returns: path to downloaded engine directory
trt_download_prebuilt_engine() {
  local repo_id="${1:-}"
  local engine_label="${2:-}"
  local target_dir="${3:-}"
  
  if [ -z "${repo_id}" ] || [ -z "${engine_label}" ]; then
    log_err "[engine] ✗ Repository ID and engine label are required"
    return 1
  fi
  
  if [ -z "${target_dir}" ]; then
    local model_name
    model_name=$(basename "${repo_id}")
    target_dir="${TRT_MODELS_DIR:-${ROOT_DIR:-.}/models}/${model_name}-trt-engine"
  fi
  
  log_info "[engine] Downloading pre-built engine: ${engine_label}"
  log_info "[engine]   From: ${repo_id}"
  log_info "[engine]   To: ${target_dir}"
  
  # Only enable HF_HUB_ENABLE_HF_TRANSFER if hf_transfer is installed
  if python -c "import hf_transfer" 2>/dev/null; then
    export HF_HUB_ENABLE_HF_TRANSFER=1
  else
    export HF_HUB_ENABLE_HF_TRANSFER=0
  fi
  
  mkdir -p "${target_dir}"
  
  if ! python -c "
import sys
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='${repo_id}',
    local_dir='${target_dir}',
    allow_patterns=['trt-llm/engines/${engine_label}/**']
)
print('✓ Downloaded pre-built engine', file=sys.stderr)
"; then
    log_err "[engine] ✗ Failed to download pre-built engine"
    return 1
  fi
  
  # Return the actual engine directory path
  local engine_dir="${target_dir}/trt-llm/engines/${engine_label}"
  if [ -d "${engine_dir}" ] && ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    echo "${engine_dir}"
    return 0
  else
    log_err "[engine] ✗ Downloaded engine directory is invalid or missing engine files"
    return 1
  fi
}

