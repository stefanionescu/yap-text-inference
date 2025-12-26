#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Detection Utilities
# =============================================================================
# TRT-specific detection: pre-quantized models, CUDA version checks.
# GPU detection: use lib/common/gpu_detect.sh functions directly.

_TRT_DETECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common GPU detection
# shellcheck source=../../lib/common/gpu_detect.sh
source "${_TRT_DETECT_DIR}/../../lib/common/gpu_detect.sh"

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


