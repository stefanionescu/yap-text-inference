#!/usr/bin/env bash
# Common helpers for scripts/

# Do not set -euo here; these functions are sourced by other scripts

# Load .env if present
load_env_if_present() {
  if [ -f ".env" ]; then
    # shellcheck disable=SC1091
    source ".env"
  fi
}

# Require an environment variable to be set (by name)
require_env() {
  local var_name="$1"
  # shellcheck disable=SC2016
  local val
  val=$(eval echo "\${$var_name:-}")
  if [ -z "$val" ]; then
    echo "[common] ERROR: $var_name not set. Export it in the shell or .env." >&2
    return 1
  fi
}

# Detect CUDA toolkit version (echoes X.Y or empty)
# Priority: nvcc (authoritative) > CUDA_VERSION env var > nvidia-smi (driver max, UNRELIABLE)
detect_cuda_version() {
  local nvcc_ver="" env_ver="" smi_ver=""

  # 1. nvcc is authoritative - it's the actual installed toolkit
  if command -v nvcc >/dev/null 2>&1; then
    nvcc_ver=$(nvcc --version 2>/dev/null | grep -oE 'release [0-9]+\.[0-9]+' | awk '{print $2}' 2>/dev/null || true)
  fi

  # 2. CUDA_VERSION env var (common in containers)
  if [ -n "${CUDA_VERSION:-}" ]; then
    env_ver=$(echo "$CUDA_VERSION" | grep -oE '^[0-9]+\.[0-9]+' 2>/dev/null || echo "$CUDA_VERSION")
  fi

  # 3. nvidia-smi shows driver's MAX supported CUDA, NOT the installed toolkit
  # Only use as last resort and warn
  if command -v nvidia-smi >/dev/null 2>&1; then
    smi_ver=$(timeout 5s nvidia-smi 2>/dev/null | grep -o "CUDA Version: [0-9][0-9]*\.[0-9]*" | awk '{print $3}' 2>/dev/null || true)
  fi

  # Return nvcc if available (most reliable)
  if [ -n "$nvcc_ver" ]; then
    # Warn if env var disagrees with nvcc
    if [ -n "$env_ver" ] && [ "$env_ver" != "$nvcc_ver" ]; then
      echo "[common] WARN: CUDA_VERSION env ($env_ver) != nvcc ($nvcc_ver); trusting nvcc" >&2
    fi
    echo "$nvcc_ver"
    return
  fi

  # Fall back to env var
  if [ -n "$env_ver" ]; then
    echo "$env_ver"
    return
  fi

  # Last resort: nvidia-smi (unreliable for toolkit version)
  if [ -n "$smi_ver" ]; then
    echo "[common] WARN: No nvcc found; using nvidia-smi CUDA $smi_ver (this is driver max, not toolkit!)" >&2
    echo "$smi_ver"
    return
  fi

  echo ""
}

# Map CUDA version to PyTorch index URL
# NOTE: TRT-LLM 1.2.0rc5 requires torch 2.9.x with CUDA 13.0
map_torch_index_url() {
  local cuda_ver="$1"
  local cuda_minor
  if [ -z "$cuda_ver" ]; then
    echo "https://download.pytorch.org/whl/cu130"
    return 0
  fi
  cuda_minor=$(echo "$cuda_ver" | cut -d. -f1-2 | tr -d '.')
  case "$cuda_minor" in
    120 | 121) echo "https://download.pytorch.org/whl/cu121" ;;
    122 | 123 | 124) echo "https://download.pytorch.org/whl/cu124" ;;
    125 | 126) echo "https://download.pytorch.org/whl/cu126" ;;
    127 | 128) echo "https://download.pytorch.org/whl/cu128" ;;
    # torch 2.9.x has cu130 wheels for CUDA 13.x
    129 | 130 | 131) echo "https://download.pytorch.org/whl/cu130" ;;
    *) echo "https://download.pytorch.org/whl/cu130" ;;
  esac
}

# Convert "X.Y" style version to integer for comparison (e.g., 13.0 -> 1300)
_version_to_int() {
  local v="${1:-}"
  if [[ $v =~ ^([0-9]+)(\.([0-9]+))? ]]; then
    local major=${BASH_REMATCH[1]}
    local minor=${BASH_REMATCH[3]:-0}
    printf "%d%02d" "$major" "$minor"
    return 0
  fi
  return 1
}

# Ensure CUDA toolkit is 13.x+ and driver supports CUDA >=13
# Checks: 1) toolkit version via nvcc/env, 2) driver capability via cudaDriverGetVersion or nvidia-smi
assert_cuda13_driver() {
  local prefix="${1:-common}"
  local min_cuda_int=1300
  local toolkit_ver toolkit_int driver_ver driver_int driver_source

  # -------------------------------------------------------------------------
  # 1. TOOLKIT CHECK: What CUDA toolkit is installed?
  # -------------------------------------------------------------------------
  toolkit_ver=$(detect_cuda_version)
  toolkit_int=$(_version_to_int "$toolkit_ver") || toolkit_int=0

  if [ "$toolkit_int" -eq 0 ]; then
    echo "[${prefix}] ERROR: Could not detect CUDA toolkit version." >&2
    echo "[${prefix}] Ensure CUDA 13.x is installed and nvcc is in PATH, or set CUDA_VERSION env var." >&2
    return 1
  fi

  if [ "$toolkit_int" -lt "$min_cuda_int" ]; then
    echo "[${prefix}] ERROR: CUDA toolkit 13.x required. Detected: '${toolkit_ver}' (int=${toolkit_int})" >&2
    echo "[${prefix}] Hint: Install CUDA 13 toolkit and ensure nvcc is in PATH." >&2
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
    echo "[${prefix}] WARN: Could not query driver CUDA capability (no cuda-python, nvidia-smi failed)." >&2
    echo "[${prefix}] Proceeding with toolkit version only - runtime errors may occur if driver is too old." >&2
    return 0
  fi

  driver_int=$(_version_to_int "$driver_ver") || driver_int=0

  if [ "$driver_int" -lt "$min_cuda_int" ]; then
    echo "[${prefix}] ERROR: NVIDIA driver only supports up to CUDA ${driver_ver} (need 13.x+)." >&2
    echo "[${prefix}] Source: ${driver_source}" >&2
    echo "[${prefix}] Hint: Upgrade to a newer NVIDIA driver that supports CUDA 13.x." >&2
    echo "[${prefix}] Your toolkit is CUDA ${toolkit_ver}, but the driver can't run CUDA 13 code." >&2
    return 1
  fi

  # Success - log what we found
  echo "[${prefix}] CUDA OK: toolkit=${toolkit_ver}, driver=${driver_ver} (via ${driver_source})" >&2
  return 0
}

# Choose a Python executable given $PYTHON_VERSION or best-effort
choose_python_exe() {
  local ver="${PYTHON_VERSION:-3.10}"
  if command -v python"${ver}" >/dev/null 2>&1; then
    echo "python${ver}"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  return 1
}

# Start a command in the background, write PID and tail logs
# Usage: start_background "<cmd>" [pid_file] [log_file]
start_background() {
  local cmd="$1"
  local pid_file="${2:-.run/server.pid}"
  local log_file="${3:-logs/server.log}"

  mkdir -p "$(dirname "$log_file")" "$(dirname "$pid_file")"
  # Fully detach from TTY so Ctrl-C on caller doesn't stop the server
  setsid bash -lc "$cmd" </dev/null >"$log_file" 2>&1 &
  local pid=$!
  echo $pid >"$pid_file"
  echo "[run] Server started in background (PID $pid)."
  echo "[run] Following logs (Ctrl-C detaches, server keeps running)"
  touch "$log_file" || true
  exec tail -n +1 -F "$log_file"
}

# Load centralized environment configuration
load_environment() {
  local env_file="${1:-scripts/lib/environment.sh}"
  if [ -f "$env_file" ]; then
    # shellcheck disable=SC1090
    source "$env_file"
  else
    echo "[common] WARNING: Environment file $env_file not found" >&2
  fi
}

# Build a uvicorn command string for this server
build_uvicorn_cmd() {
  local host="${HOST:-0.0.0.0}"
  local port="${PORT:-8000}"
  echo "uvicorn server.server:app --host \"$host\" --port \"$port\" --timeout-keep-alive 75 --log-level info"
}
