#!/usr/bin/env bash
# =============================================================================
# Build Helpers for TensorRT-LLM Engine
# =============================================================================
# Sourced by step scripts and orchestrator. Do NOT `set -euo` here.

# Assumes the following are already sourced by orchestrator:
#   source "scripts/lib/common.sh"
#   load_env_if_present
#   load_environment

if [ -z "${__ORPHEUS_BUILD_CONFIG_LIB_SOURCED:-}" ]; then
  _helpers_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  # shellcheck disable=SC1090
  source "${_helpers_root}/scripts/build/config.sh"
  __ORPHEUS_BUILD_CONFIG_LIB_SOURCED=1
  unset _helpers_root
fi

_setup_huggingface_auth() {
  if [ -n "${HF_TOKEN:-}" ]; then
    export HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-$HF_TOKEN}"
    export HF_HUB_TOKEN="${HF_HUB_TOKEN:-$HF_TOKEN}"
  else
    echo "ERROR: HF_TOKEN not set" >&2
    return 1
  fi
}

# Get file size in bytes (cross-platform: macOS + Linux)
_file_size() {
  local file="$1"
  stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0"
}

_should_skip_build() {
  if [ "${FORCE_REBUILD:-false}" = true ]; then
    return 1 # Force rebuild
  fi
  # Check if config changed from previous build
  if _build_config_changed; then
    echo "[build:helpers] Configuration changed from previous build - will rebuild"
    # Set FORCE_REBUILD so step scripts also rebuild
    export FORCE_REBUILD=true
    # Clean up old artifacts for the NEW precision mode paths
    _cleanup_old_build_artifacts
    return 1 # Need to rebuild
  fi
  if [ -f "${ENGINE_OUTPUT_DIR}/rank0.engine" ] && [ -f "${ENGINE_OUTPUT_DIR}/config.json" ]; then
    return 0 # Skip build
  fi
  return 1 # Need to build
}

# Clean up old checkpoint and engine directories for current precision mode
_cleanup_old_build_artifacts() {
  local precision="${ORPHEUS_PRECISION_MODE:-quantized}"
  local ckpt_dir engine_dir
  
  if [[ "$precision" == "base" ]]; then
    ckpt_dir="${CHECKPOINT_DIR:-${ROOT_DIR:-.}/models/orpheus-trtllm-ckpt-8bit}"
    engine_dir="${ENGINE_OUTPUT_DIR:-${ROOT_DIR:-.}/models/orpheus-trt-8bit}"
  else
    ckpt_dir="${CHECKPOINT_DIR:-${ROOT_DIR:-.}/models/orpheus-trtllm-ckpt-int4-awq}"
    engine_dir="${ENGINE_OUTPUT_DIR:-${ROOT_DIR:-.}/models/orpheus-trt-awq}"
  fi
  
  if [[ -d "$ckpt_dir" ]]; then
    echo "[build:helpers] Removing old checkpoint: $ckpt_dir"
    rm -rf "$ckpt_dir"
  fi
  if [[ -d "$engine_dir" ]]; then
    echo "[build:helpers] Removing old engine: $engine_dir"
    rm -rf "$engine_dir"
  fi
}

# Check if build configuration changed from previous build
# Returns 0 if config changed (need rebuild), 1 if unchanged
_build_config_changed() {
  local config_file="${ROOT_DIR:-.}/.run/build_config.env"
  orpheus_build_config_changed "$config_file" "[build:helpers]"
}

_detect_gpu_sm_arch() {
  # Echoes an smXX string if detectable, otherwise empty
  local sm_env="${GPU_SM_ARCH:-}"
  if [ -n "$sm_env" ]; then
    echo "$sm_env"
    return 0
  fi
  if command -v nvidia-smi >/dev/null 2>&1; then
    local cap
    cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 | tr -d '\r' | tr -d '\n')
    if [ -n "$cap" ]; then
      local major minor
      major=$(echo "$cap" | cut -d. -f1)
      minor=$(echo "$cap" | cut -d. -f2)
      echo "sm${major}${minor}"
      return 0
    fi
  fi
  echo ""
}

_detect_gpu_name() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 | tr -d '\r' | tr -d '\n'
  else
    echo ""
  fi
}

_gpu_supports_fp8() {
  local sm
  sm=$(_detect_gpu_sm_arch)
  if [ -z "$sm" ]; then
    return 1
  fi
  local digits="${sm#sm}"
  if [[ -z $digits ]]; then
    return 1
  fi
  local num=$((10#$digits))
  # FP8 supported on Ada Lovelace (sm89) and Hopper+ (sm90+)
  if ((num >= 90)); then
    return 0
  fi
  if ((num == 89)); then
    return 0
  fi
  return 1
}

# Resolve quantization format for base mode based on GPU capability
# Returns: fp8 (for Ada/Hopper GPUs) or full_prec (for Ampere and older)
# Note: INT8 formats (int8_wo, int8_sq, w4a8_awq) all cause severe quality degradation
# on speech models like Orpheus. On non-FP8 GPUs, full precision is the only option
# that works reliably.
_resolve_base_qformat() {
  if _gpu_supports_fp8; then
    echo "fp8"
  else
    echo "full_prec"
  fi
}

# Resolve KV cache dtype for base mode quantization
# Returns: fp8 (for FP8 qformat) or None (for full_prec - uses model dtype)
_resolve_base_kv_cache_dtype() {
  local qformat="${1:-$(_resolve_base_qformat)}"
  case "$qformat" in
    fp8) echo "fp8" ;;
    full_prec) echo "none" ;;  # Use model dtype (no KV cache quantization)
    *) echo "int8" ;;
  esac
}

# Legacy function - kept for compatibility but now just returns float16
# The actual precision is determined by _resolve_base_qformat()
_resolve_base_inference_dtype() {
  # dtype is always float16 (the qformat handles quantization if any)
  echo "float16"
}

_validate_downloaded_checkpoint() {
  local ckpt_dir="$1"
  echo "[build:helpers] Validating downloaded checkpoint at $ckpt_dir"
  test -f "$ckpt_dir/config.json" || {
    echo "[build:helpers] ERROR: Missing config.json in $ckpt_dir" >&2
    return 1
  }
  ls "$ckpt_dir"/rank*.safetensors >/dev/null 2>&1 || {
    echo "[build:helpers] ERROR: No rank*.safetensors found in $ckpt_dir" >&2
    return 1
  }
  echo "[build:helpers] Checkpoint validation passed"
}

_validate_downloaded_engine() {
  local eng_dir="$1"
  echo "[build:helpers] Validating downloaded engine at $eng_dir"
  test -f "$eng_dir/rank0.engine" || {
    echo "[build:helpers] ERROR: Missing rank0.engine in $eng_dir" >&2
    return 1
  }
  test -f "$eng_dir/config.json" || {
    echo "[build:helpers] ERROR: Missing config.json in $eng_dir" >&2
    return 1
  }
  local eng_size
  eng_size=$(_file_size "$eng_dir/rank0.engine")
  if [ "$eng_size" -lt 1000000 ]; then
    echo "WARNING: Engine file seems unusually small ($eng_size bytes)" >&2
  fi
  echo "[build:helpers] Engine files present"
}

_engine_env_compatible() {
  # Returns 0 if compatible or non-strict; 1 if strict mismatch
  local eng_dir="$1"
  local strict="${HF_DEPLOY_STRICT_ENV_MATCH:-1}"
  if [ "$strict" != "1" ]; then
    return 0
  fi
  local want_sm
  want_sm=$(_detect_gpu_sm_arch)
  if [ -z "$want_sm" ]; then
    return 0
  fi
  local meta_file="$eng_dir/build_metadata.json"
  if [ -f "$meta_file" ]; then
    local sm_in_meta
    sm_in_meta=$(
      python - "$meta_file" <<'PY'
import json,sys
p=sys.argv[1]
try:
    with open(p,'r') as f:
        d=json.load(f)
    print((d.get('sm_arch') or '').strip())
except Exception:
    print('')
PY
    )
    if [ -n "$sm_in_meta" ] && [ "$sm_in_meta" != "$want_sm" ]; then
      echo "[build:helpers] Engine SM mismatch: repo=$sm_in_meta local=$want_sm" >&2
      return 1
    fi
  else
    local base
    base=$(basename "$eng_dir")
    case "$base" in
      ${want_sm}_*) : ;;
      *)
        echo "[build:helpers] Engine label likely incompatible with local SM ($want_sm): $base" >&2
        return 1
        ;;
    esac
  fi
  return 0
}

_record_engine_dir_env() {
  local eng_dir="$1"
  mkdir -p .run
  echo "export TRTLLM_ENGINE_DIR=\"$eng_dir\"" >.run/engine_dir.env
}

_validate_engine() {
  echo "[build:helpers] Validating built engine..."
  local required_files=("rank0.engine" "config.json")
  for file in "${required_files[@]}"; do
    if [ ! -f "$ENGINE_OUTPUT_DIR/$file" ]; then
      echo "ERROR: Required file missing: $ENGINE_OUTPUT_DIR/$file" >&2
      return 1
    fi
  done
  local engine_size
  engine_size=$(_file_size "$ENGINE_OUTPUT_DIR/rank0.engine")
  if [ "$engine_size" -lt 1000000 ]; then
    echo "WARNING: Engine file seems unusually small ($engine_size bytes)" >&2
  fi
  echo "[build:helpers] Engine validation passed"
}
