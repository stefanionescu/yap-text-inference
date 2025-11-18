#!/usr/bin/env bash

AWQ_DIR="${ROOT_DIR}/models"
# shellcheck disable=SC2034  # referenced by sourced AWQ helpers
CHAT_AWQ_DIR="${AWQ_DIR}/chat_awq"
# shellcheck disable=SC2034  # referenced by sourced AWQ helpers
TOOL_AWQ_DIR="${AWQ_DIR}/tool_awq"
mkdir -p "${AWQ_DIR}"

quantize_model() {
  local name="$1"; local src="$2"; local out_dir="$3"; local commit_msg="$4"; local repo_var="$5"
  if [ -d "${out_dir}" ] && { [ -f "${out_dir}/awq_config.json" ] || [ -f "${out_dir}/.awq_ok" ]; }; then
    log_info "Using existing AWQ ${name} at ${out_dir}"
    echo "${out_dir}"
    return 0
  fi
  log_info "Quantizing ${name} model to AWQ: ${src} -> ${out_dir}"
  if cd "${ROOT_DIR}" && \
     "/opt/venv/bin/python" -m src.awq.quantize --model "${src}" --out "${out_dir}"; then
    push_awq_to_hf "${out_dir}" "${repo_var}" "${commit_msg}"
    echo "${out_dir}"
    return 0
  fi
  return 1
}


