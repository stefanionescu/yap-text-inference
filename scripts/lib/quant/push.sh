#!/usr/bin/env bash

# Push AWQ artifacts to Hugging Face repo

push_awq_to_hf() {
  local src_dir="$1"
  local repo_id="$2"
  local commit_msg="$3"

  if [ "${HF_AWQ_PUSH}" != "1" ]; then
    return
  fi

  if [ -z "${repo_id}" ] || [[ "${repo_id}" == your-org/* ]]; then
    log_warn "HF_AWQ_PUSH=1 but Hugging Face repo not configured; skipping upload for ${src_dir}"
    return
  fi

  if [[ "${repo_id}" == /* ]]; then
    log_warn "HF_AWQ_PUSH=1 but repo id '${repo_id}' looks like a local path; skipping upload"
    return
  fi

  if [ -z "${HF_TOKEN:-}" ]; then
    log_warn "HF_AWQ_PUSH=1 but no Hugging Face token available; skipping upload"
    return
  fi

  if [ ! -d "${src_dir}" ]; then
    log_warn "HF AWQ push skipped; directory not found: ${src_dir}"
    return
  fi

  local python_cmd=("${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/src/awq/hf/hf_push.py" --src "${src_dir}" --repo-id "${repo_id}" --branch "${HF_AWQ_BRANCH}" --token "${HF_TOKEN}")
  if [ "${HF_AWQ_PRIVATE}" = "1" ]; then
    python_cmd+=(--private)
  fi
  if [ "${HF_AWQ_ALLOW_CREATE}" != "1" ]; then
    python_cmd+=(--no-create)
  fi
  if [ -n "${commit_msg}" ]; then
    python_cmd+=(--commit-message "${commit_msg}")
  fi

  log_info "Uploading AWQ weights from ${src_dir} to Hugging Face repo ${repo_id}"
  HF_TOKEN="${HF_TOKEN}" "${python_cmd[@]}"
}


