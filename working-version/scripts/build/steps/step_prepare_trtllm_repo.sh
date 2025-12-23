#!/usr/bin/env bash
set -euo pipefail

source "scripts/lib/common.sh"
load_env_if_present
load_environment
source "scripts/build/helpers.sh"

precision_mode="${ORPHEUS_PRECISION_MODE:-quantized}"
if [[ $precision_mode == "base" ]]; then
  echo "[build:trtllm-repo] Preparing TensorRT-LLM repository"
else
  echo "[build:trtllm-repo] Preparing TensorRT-LLM repository (quantization scripts)"
fi

TRTLLM_REPO_DIR="${TRTLLM_REPO_DIR:-$PWD/.trtllm-repo}"
# Use TRTLLM_REPO_URL from environment.sh (standardized name)
TRTLLM_REPO_URL="${TRTLLM_REPO_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}"
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
TRTLLM_REPO_RESET="${TRTLLM_REPO_RESET:-0}"
TRTLLM_TARGET_VERSION="${TRTLLM_TARGET_VERSION:-1.2.0rc5}"
TRTLLM_CLONE_DEPTH="${TRTLLM_CLONE_DEPTH:-1}"
TRTLLM_CLONE_FILTER="${TRTLLM_CLONE_FILTER:-blob:none}"
TRTLLM_TAG_FETCH_DEPTH="${TRTLLM_TAG_FETCH_DEPTH:-1}"

echo "[build:trtllm-repo] Detecting TensorRT-LLM version..."
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
  echo "[build:trtllm-repo] WARN: Unable to detect installed tensorrt-llm version, defaulting to ${TRTLLM_TARGET_VERSION}" >&2
  trtllm_ver="${TRTLLM_TARGET_VERSION}"
fi
if [ "${trtllm_ver}" != "${TRTLLM_TARGET_VERSION}" ]; then
  echo "[build:trtllm-repo] WARN: Installed tensorrt-llm version (${trtllm_ver}) differs from required ${TRTLLM_TARGET_VERSION}." >&2
  echo "[build:trtllm-repo] WARN: Continuing with target version ${TRTLLM_TARGET_VERSION}; ensure your environment matches." >&2
  trtllm_ver="${TRTLLM_TARGET_VERSION}"
fi

echo "[build:trtllm-repo] Target TensorRT-LLM version: ${trtllm_ver}"
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

# Silence git debug logging by default; opt-in via env if needed.
if [ -z "${GIT_CURL_VERBOSE+x}" ]; then
  unset GIT_CURL_VERBOSE
fi
if [ -z "${GIT_TRACE+x}" ]; then
  unset GIT_TRACE
fi

if [ -d "${TRTLLM_REPO_DIR}" ]; then
  if [ "${TRTLLM_REPO_RESET}" = "1" ]; then
    echo "[build:trtllm-repo] TRTLLM_REPO_RESET=1 → removing existing repository"
    rm -rf "${TRTLLM_REPO_DIR}"
  else
    echo "[build:trtllm-repo] Reusing existing repository at ${TRTLLM_REPO_DIR}"
    echo "[build:trtllm-repo]   (set TRTLLM_REPO_RESET=1 if you need a clean clone)"
  fi
fi

if [ ! -d "${TRTLLM_REPO_DIR}" ]; then
  if [[ $precision_mode == "base" ]]; then
    echo "[build:trtllm-repo] Cloning TensorRT-LLM repo for base converters..."
  else
    echo "[build:trtllm-repo] Cloning TensorRT-LLM repo for quantization tools..."
  fi

  clone_attempts="${TRTLLM_CLONE_ATTEMPTS:-5}"
  clone_delay="${TRTLLM_CLONE_BACKOFF_SECONDS:-2}"
  clone_opts=("--quiet" "--single-branch" "--no-tags" "--branch" "${clone_ref}")
  if [ "${shallow_clone_enabled}" = true ]; then
    clone_opts+=("--depth" "${TRTLLM_CLONE_DEPTH}")
    if [ -n "${TRTLLM_CLONE_FILTER}" ] && [ "${TRTLLM_CLONE_FILTER}" != "none" ]; then
      clone_opts+=("--filter=${TRTLLM_CLONE_FILTER}")
    fi
  fi
  attempt=1
  clone_done=false
  while [ "${attempt}" -le "${clone_attempts}" ]; do
    echo "[build:trtllm-repo] Clone attempt ${attempt}/${clone_attempts}"
    if git -c http.lowSpeedLimit=0 -c http.lowSpeedTime=999999 -c advice.detachedHead=false clone "${clone_opts[@]}" "${TRTLLM_REPO_URL}" "${TRTLLM_REPO_DIR}"; then
      clone_done=true
      break
    fi
    echo "[build:trtllm-repo] Clone attempt ${attempt} failed; cleaning partial checkout and retrying..."
    rm -rf "${TRTLLM_REPO_DIR}"
    attempt=$((attempt + 1))
    if [ "${attempt}" -le "${clone_attempts}" ]; then
      sleep "${clone_delay}"
      clone_delay=$((clone_delay * 2))
    fi
  done

  if [ "${clone_done}" != true ]; then
    echo "[build:trtllm-repo] ERROR: Failed to clone TensorRT-LLM repo after ${clone_attempts} attempts" >&2
    exit 1
  fi
fi

echo "[build:trtllm-repo] Syncing repo to ${tag_name}"
if git -C "${TRTLLM_REPO_DIR}" show-ref --verify --quiet "${tag_ref}"; then
  echo "[build:trtllm-repo] Tag ${tag_name} already present locally"
else
  echo "[build:trtllm-repo] Fetching ${tag_ref} (depth=${TRTLLM_TAG_FETCH_DEPTH})"
  if [ "${shallow_clone_enabled}" = true ] && [ "${shallow_tag_fetch_enabled}" = true ]; then
    git -C "${TRTLLM_REPO_DIR}" fetch --quiet --depth "${TRTLLM_TAG_FETCH_DEPTH}" --force origin "${tag_ref}:${tag_ref}" || {
      echo "[build:trtllm-repo] ERROR: Unable to fetch ${tag_ref}" >&2
      exit 1
    }
  else
    git -C "${TRTLLM_REPO_DIR}" fetch --quiet --force origin "${tag_ref}:${tag_ref}" || {
      echo "[build:trtllm-repo] ERROR: Unable to fetch ${tag_ref}" >&2
      exit 1
    }
  fi
fi

if ! git -c advice.detachedHead=false -C "${TRTLLM_REPO_DIR}" checkout --quiet "${tag_name}" 2>/dev/null; then
  echo "[build:trtllm-repo] ERROR: Could not checkout version ${trtllm_ver} (tag ${tag_name})" >&2
  echo "[build:trtllm-repo] Hint: ensure ${tag_name} exists in ${TRTLLM_REPO_URL}" >&2
  exit 1
fi

if [[ $precision_mode == "quantized" ]]; then
  if [ ! -d "$TRTLLM_REPO_DIR/examples/quantization" ]; then
    echo "[build:trtllm-repo] ERROR: quantization examples not found in $TRTLLM_REPO_DIR/examples/quantization" >&2
    echo "[build:trtllm-repo] Available examples:" >&2
    ls -la "$TRTLLM_REPO_DIR/examples/" >&2
    exit 1
  fi
  export TRTLLM_EXAMPLES_DIR="$TRTLLM_REPO_DIR/examples/quantization"
  echo "[build:trtllm-repo] Quantization utilities ready"
else
  echo "[build:trtllm-repo] Converter utilities ready"
fi
