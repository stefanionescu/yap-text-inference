#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Repository Helpers
# =============================================================================

_TRT_REPO_HELPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
# shellcheck source=./config.sh
source "${_TRT_REPO_HELPER_DIR}/config.sh"

if ! type pip_quiet >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  # shellcheck source=../deps/pip.sh
  source "${_TRT_REPO_HELPER_DIR}/../deps/pip.sh"
fi

# Clone or update TensorRT-LLM repository for quantization scripts
trt_prepare_repo() {
  local repo_url="${TRT_REPO_URL}"
  local repo_dir="${TRT_REPO_DIR}"
  local tag_name="${TRT_REPO_TAG}"
  local tag_ref="refs/tags/${tag_name}"
  local clone_depth="${TRT_CLONE_DEPTH}"
  local clone_filter="${TRT_CLONE_FILTER}"
  local clone_attempts="${TRT_CLONE_ATTEMPTS}"
  local clone_delay="${TRT_CLONE_BACKOFF_SECONDS}"

  if [ -d "${repo_dir}" ]; then
    log_info "[trt] Reusing existing TensorRT-LLM repository..."
  else
    log_info "[trt] Cloning TRTLLM repo..."
    local clone_opts=("--quiet" "--single-branch" "--no-tags" "--branch" "${tag_name}")
    if [ "${clone_depth}" != "full" ]; then
      clone_opts+=("--depth" "${clone_depth}")
      if [ -n "${clone_filter}" ] && [ "${clone_filter}" != "none" ]; then
        clone_opts+=("--filter=${clone_filter}")
      fi
    fi

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

  if git -C "${repo_dir}" show-ref --verify --quiet "${tag_ref}" >/dev/null 2>&1; then
    :
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

  if [ ! -d "${repo_dir}/examples/quantization" ]; then
    log_err "[trt] ✗ Quantization examples not found in ${repo_dir}/examples/quantization"
    ls -la "${repo_dir}/examples/" >&2
    return 1
  fi

  export TRT_REPO_DIR="${repo_dir}"
  return 0
}

# Install quantization requirements from the TRT-LLM repository
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

    mkdir -p "$(dirname "${filtered_reqs}")"

    # Filter dependencies handled elsewhere to avoid CUDA wheel mismatch.
    awk '
      BEGIN { IGNORECASE = 1 }
      /^(torch==|torchvision==|nvidia-cuda-runtime|nvidia-cudnn|nvidia-cublas|nvidia-cusparse|nvidia-cusolver|nvidia-cufft|nvidia-curand|nvidia-nvjitlink|nvidia-nvtx|cuda-toolkit)/ { next }
      /^[[:space:]]*-c[[:space:]]+\.\.\/constraints\.txt/ { next }
      { print }
    ' "${quant_reqs}" >"${filtered_reqs}" || cp "${quant_reqs}" "${filtered_reqs}"

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

    mkdir -p "$(dirname "${marker_file}")"
    md5sum "${quant_reqs}" 2>/dev/null | awk '{print $1}' >"${marker_file}"
    log_info "[trt] ✓ Quantization dependencies installed"
    log_blank
  else
    log_warn "[trt] ⚠ Quantization requirements.txt not found at ${quant_reqs}, continuing"
  fi
}
