#!/usr/bin/env bash

# Requirements installation helpers (excluding FlashInfer)

filter_requirements_without_flashinfer() {
  local req_file="${ROOT_DIR}/requirements.txt"
  local tmp_req_file="${ROOT_DIR}/.venv/.requirements.no_flashinfer.txt"
  if [ -f "${req_file}" ]; then
    grep -v -E '^\s*flashinfer-python(\s|$|==|>=|<=|~=|!=)' "${req_file}" > "${tmp_req_file}" || cp "${req_file}" "${tmp_req_file}" || true
  fi
}

should_skip_requirements_install() {
  local req_file="${ROOT_DIR}/requirements.txt"
  local stamp_file="${ROOT_DIR}/.venv/.req_hash"
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
  local tmp_req_file="${ROOT_DIR}/.venv/.requirements.no_flashinfer.txt"
  if ! should_skip_requirements_install; then
    "${ROOT_DIR}/.venv/bin/pip" install --upgrade-strategy only-if-needed -r "${tmp_req_file}"
  else
    log_info "Dependencies unchanged; skipping main pip install"
  fi
}

record_requirements_hash() {
  local req_file="${ROOT_DIR}/requirements.txt"
  local stamp_file="${ROOT_DIR}/.venv/.req_hash"
  if [ -f "${req_file}" ]; then
    sha256sum "${req_file}" | awk '{print $1}' > "${stamp_file}" || true
  fi
}


