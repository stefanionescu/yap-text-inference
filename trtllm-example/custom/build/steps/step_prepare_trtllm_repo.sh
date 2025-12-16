#!/usr/bin/env bash
set -euo pipefail

source "custom/lib/common.sh"
load_env_if_present
load_environment "$@"
source "custom/build/helpers.sh"

precision_mode="${ORPHEUS_PRECISION_MODE:-quantized}"
if [[ $precision_mode == "base" ]]; then
  echo "[step:trtllm] Preparing TensorRT-LLM repository (converter scripts)"
else
  echo "[step:trtllm] Preparing TensorRT-LLM repository (quantization scripts)"
fi

TRTLLM_REPO_DIR="${TRTLLM_REPO_DIR:-$PWD/.trtllm-repo}"
TRTLLM_REMOTE_URL="${TRTLLM_REMOTE_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}"
VENV_DIR="${VENV_DIR:-$PWD/.venv}"
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090,SC1091
  source "$VENV_DIR/bin/activate"
fi
PYTHON_EXEC="${PYTHON_EXEC:-${VENV_DIR}/bin/python}"
if [ ! -x "$PYTHON_EXEC" ]; then
  PYTHON_EXEC="python"
fi
FORCE_REBUILD="${FORCE_REBUILD:-false}"
TRTLLM_TARGET_VERSION="${TRTLLM_TARGET_VERSION:-1.2.0rc5}"
TRTLLM_CLONE_DEPTH="${TRTLLM_CLONE_DEPTH:-1}"
TRTLLM_CLONE_FILTER="${TRTLLM_CLONE_FILTER:-blob:none}"
TRTLLM_TAG_FETCH_DEPTH="${TRTLLM_TAG_FETCH_DEPTH:-1}"

echo "[step:trtllm] Detecting TensorRT-LLM version..."
trtllm_ver="$(
  ${PYTHON_EXEC} - <<'PY'
import importlib.metadata
try:
    print(importlib.metadata.version("tensorrt-llm"))
except importlib.metadata.PackageNotFoundError:
    pass
PY
)"
trtllm_ver="$(echo "${trtllm_ver}" | tail -1 | tr -d '[:space:]')"
if [ -z "${trtllm_ver}" ]; then
  trtllm_ver="$(${PYTHON_EXEC} -c 'import tensorrt_llm as t; print(t.__version__)' 2>/dev/null | tail -1 | tr -d '[:space:]')"
fi
if [ -z "${trtllm_ver}" ]; then
  echo "[step:trtllm] WARN: Unable to detect installed tensorrt-llm version, defaulting to ${TRTLLM_TARGET_VERSION}" >&2
  trtllm_ver="${TRTLLM_TARGET_VERSION}"
fi
if [ "${trtllm_ver}" != "${TRTLLM_TARGET_VERSION}" ]; then
  echo "[step:trtllm] WARN: Installed tensorrt-llm version (${trtllm_ver}) differs from required ${TRTLLM_TARGET_VERSION}." >&2
  echo "[step:trtllm] WARN: Continuing with target version ${TRTLLM_TARGET_VERSION}; ensure your environment matches." >&2
  trtllm_ver="${TRTLLM_TARGET_VERSION}"
fi

echo "[step:trtllm] Target TensorRT-LLM version: ${trtllm_ver}"
tag_name="v${trtllm_ver}"
tag_ref="refs/tags/${tag_name}"
clone_ref="${tag_name}"

shallow_clone_enabled=true
if [ "${TRTLLM_CLONE_DEPTH}" = "full" ]; then
  shallow_clone_enabled=false
fi
shallow_tag_fetch_enabled=true
if [ "${TRTLLM_TAG_FETCH_DEPTH}" = "full" ]; then
  shallow_tag_fetch_enabled=false
fi

export GIT_CURL_VERBOSE="${GIT_CURL_VERBOSE:-1}"
export GIT_TRACE="${GIT_TRACE:-1}"

if [ "$FORCE_REBUILD" = true ] && [ -d "${TRTLLM_REPO_DIR}" ]; then
  echo "[step:trtllm] --force specified: removing existing repository"
  rm -rf "${TRTLLM_REPO_DIR}"
fi

if [ ! -d "${TRTLLM_REPO_DIR}" ]; then
  if [[ $precision_mode == "base" ]]; then
    echo "[step:trtllm] Cloning TensorRT-LLM repo for base converters..."
  else
    echo "[step:trtllm] Cloning TensorRT-LLM repo for quantization tools..."
  fi

  clone_attempts="${TRTLLM_CLONE_ATTEMPTS:-5}"
  clone_delay="${TRTLLM_CLONE_BACKOFF_SECONDS:-2}"
  clone_opts=("--single-branch" "--no-tags" "--branch" "${clone_ref}")
  if [ "${shallow_clone_enabled}" = true ]; then
    clone_opts+=("--depth" "${TRTLLM_CLONE_DEPTH}")
    if [ -n "${TRTLLM_CLONE_FILTER}" ] && [ "${TRTLLM_CLONE_FILTER}" != "none" ]; then
      clone_opts+=("--filter=${TRTLLM_CLONE_FILTER}")
    fi
  fi
  attempt=1
  clone_done=false
  while [ "${attempt}" -le "${clone_attempts}" ]; do
    echo "[step:trtllm] Clone attempt ${attempt}/${clone_attempts}"
    if git -c http.lowSpeedLimit=0 -c http.lowSpeedTime=999999 clone "${clone_opts[@]}" "${TRTLLM_REMOTE_URL}" "${TRTLLM_REPO_DIR}"; then
      clone_done=true
      break
    fi
    echo "[step:trtllm] Clone attempt ${attempt} failed; cleaning partial checkout and retrying..."
    rm -rf "${TRTLLM_REPO_DIR}"
    attempt=$((attempt + 1))
    if [ "${attempt}" -le "${clone_attempts}" ]; then
      sleep "${clone_delay}"
      clone_delay=$((clone_delay * 2))
    fi
  done

  if [ "${clone_done}" != true ]; then
    echo "[step:trtllm] ERROR: Failed to clone TensorRT-LLM repo after ${clone_attempts} attempts" >&2
    exit 1
  fi
fi

echo "[step:trtllm] Syncing repo to ${tag_name}"
if git -C "${TRTLLM_REPO_DIR}" show-ref --verify --quiet "${tag_ref}"; then
  echo "[step:trtllm] Tag ${tag_name} already present locally"
else
  echo "[step:trtllm] Fetching ${tag_ref} (depth=${TRTLLM_TAG_FETCH_DEPTH})"
  if [ "${shallow_clone_enabled}" = true ] && [ "${shallow_tag_fetch_enabled}" = true ]; then
    git -C "${TRTLLM_REPO_DIR}" fetch --depth "${TRTLLM_TAG_FETCH_DEPTH}" --force origin "${tag_ref}:${tag_ref}" || {
      echo "[step:trtllm] ERROR: Unable to fetch ${tag_ref}" >&2
      exit 1
    }
  else
    git -C "${TRTLLM_REPO_DIR}" fetch --force origin "${tag_ref}:${tag_ref}" || {
      echo "[step:trtllm] ERROR: Unable to fetch ${tag_ref}" >&2
      exit 1
    }
  fi
fi

if ! git -C "${TRTLLM_REPO_DIR}" checkout "${tag_name}" 2>/dev/null; then
  echo "[step:trtllm] ERROR: Could not checkout version ${trtllm_ver} (tag ${tag_name})" >&2
  echo "[step:trtllm] Hint: ensure ${tag_name} exists in ${TRTLLM_REMOTE_URL}" >&2
  exit 1
fi

if [[ $precision_mode == "quantized" ]]; then
  if [ ! -d "$TRTLLM_REPO_DIR/examples/quantization" ]; then
    echo "ERROR: quantization examples not found in $TRTLLM_REPO_DIR/examples/quantization" >&2
    echo "Available examples:" >&2
    ls -la "$TRTLLM_REPO_DIR/examples/" >&2
    exit 1
  fi
  export TRTLLM_EXAMPLES_DIR="$TRTLLM_REPO_DIR/examples/quantization"
  echo "[step:trtllm] Quantization utilities ready"
else
  echo "[step:trtllm] Converter utilities ready"
fi
