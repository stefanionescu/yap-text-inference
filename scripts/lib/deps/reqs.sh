#!/usr/bin/env bash

# Requirements installation helpers (excluding FlashInfer)

# Get the correct requirements file based on inference engine
get_requirements_file() {
  local engine="${INFERENCE_ENGINE:-vllm}"
  case "${engine}" in
    trt|TRT)
      echo "${ROOT_DIR}/requirements-trt.txt"
      ;;
    *)
      echo "${ROOT_DIR}/requirements-vllm.txt"
      ;;
  esac
}

filter_requirements_without_flashinfer() {
  local req_file
  req_file="$(get_requirements_file)"
  local venv_dir
  venv_dir="$(get_venv_dir)"
  local tmp_req_file="${venv_dir}/.requirements.no_flashinfer.txt"
  if [ -f "${req_file}" ]; then
    grep -v -E '^\s*(flashinfer-python)(\s|$|==|>=|<=|~=|!=)' "${req_file}" > "${tmp_req_file}" || cp "${req_file}" "${tmp_req_file}" || true
  fi
}

should_skip_requirements_install() {
  local req_file
  req_file="$(get_requirements_file)"
  local venv_dir
  venv_dir="$(get_venv_dir)"
  local stamp_file="${venv_dir}/.req_hash"
  if [ "${FORCE_REINSTALL:-0}" != "1" ] && [ -f "${stamp_file}" ] && [ -f "${req_file}" ]; then
    local cur_hash
    local old_hash
    cur_hash=$(sha256sum "${req_file}" | awk '{print $1}')
    old_hash=$(cat "${stamp_file}" 2>/dev/null || true)
    if [ "${cur_hash}" = "${old_hash}" ]; then
      return 0
    fi
  fi
  return 1
}

install_requirements_without_flashinfer() {
  local venv_dir
  venv_dir="$(get_venv_dir)"
  local tmp_req_file="${venv_dir}/.requirements.no_flashinfer.txt"
  if ! should_skip_requirements_install; then
    "${venv_dir}/bin/pip" install --upgrade-strategy only-if-needed -r "${tmp_req_file}"
  else
    log_info "[deps] Dependencies unchanged; skipping main pip install"
  fi
}

record_requirements_hash() {
  local req_file
  req_file="$(get_requirements_file)"
  local venv_dir
  venv_dir="$(get_venv_dir)"
  local stamp_file="${venv_dir}/.req_hash"
  if [ -f "${req_file}" ]; then
    sha256sum "${req_file}" | awk '{print $1}' > "${stamp_file}" || true
  fi
}
