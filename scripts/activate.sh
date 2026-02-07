#!/usr/bin/env bash
# =============================================================================
# Virtual Environment Activation Helper
# =============================================================================
# Helper to enter the correct virtual environment (repo .venv, /opt/venv, or
# a custom VENV_DIR). Runs commands inside the environment or opens an
# interactive shell when invoked without arguments.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
export ROOT_DIR

# shellcheck disable=SC1090
source "${SCRIPT_DIR}/lib/noise/python.sh"
# shellcheck disable=SC1090
source "${SCRIPT_DIR}/lib/common/log.sh"
# shellcheck disable=SC1090
source "${SCRIPT_DIR}/lib/deps/venv.sh"
source "${SCRIPT_DIR}/lib/env/runtime.sh"

venv_dir="$(get_venv_dir)"
activate_script="${venv_dir}/bin/activate"

if [ ! -f "${activate_script}" ]; then
  log_err "[activate] ✗ Virtual environment missing at ${venv_dir}"
  log_err "[activate] ✗ Run 'bash scripts/steps/03_install_deps.sh' (or the main launcher) to create it."
  exit 1
fi

if [ "$#" -gt 0 ]; then
  # shellcheck disable=SC1091
  source "${activate_script}"
  log_info "[activate] Running inside ${venv_dir}: $*"
  exec "$@"
fi

target_shell="${SHELL:-/bin/bash}"
shell_name="$(basename "${target_shell}")"

runtime_init_repo_paths "${ROOT_DIR}"

launch_bash_shell() {
  local rc_file="${RUN_DIR}/activate.bashrc"
  cat >"${rc_file}" <<EOF
if [ -f "\${HOME}/.bashrc" ]; then
  source "\${HOME}/.bashrc"
fi
source "${activate_script}"
EOF
  log_info "[activate] Dropping into bash with ${venv_dir} activated"
  exec /bin/bash --rcfile "${rc_file}" -i
}

case "${shell_name}" in
  bash)
    launch_bash_shell
    ;;
  zsh)
    zdotdir="${RUN_DIR}/activate-zdotdir"
    mkdir -p "${zdotdir}"
    cat >"${zdotdir}/.zshrc" <<EOF
if [ -f "\${HOME}/.zshrc" ]; then
  source "\${HOME}/.zshrc"
fi
source "${activate_script}"
EOF
    export ZDOTDIR="${zdotdir}"
    log_info "[activate] Dropping into zsh with ${venv_dir} activated"
    exec "${target_shell}" -i
    ;;
  *)
    log_warn "[activate] ⚠ Shell '${shell_name}' not recognized; falling back to bash."
    launch_bash_shell
    ;;
esac
