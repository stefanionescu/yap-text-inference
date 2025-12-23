#!/usr/bin/env bash
#
# Helper to enter the correct virtual environment (repo .venv, /opt/venv, or a
# custom VENV_DIR). When invoked with a command, it runs that command inside the
# environment. When invoked without arguments, it opens an interactive shell
# with the environment already activated.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
export ROOT_DIR

# shellcheck disable=SC1090
source "${SCRIPT_DIR}/lib/common/log.sh"
# shellcheck disable=SC1090
source "${SCRIPT_DIR}/lib/deps/venv.sh"

venv_dir="$(resolve_venv_dir)"
activate_script="${venv_dir}/bin/activate"

if [ ! -f "${activate_script}" ]; then
  log_err "[activate] Virtual environment missing at ${venv_dir}"
  log_err "[activate] Run 'bash scripts/steps/03_install_deps.sh' (or the main launcher) to create it."
  exit 1
fi

# shellcheck disable=SC1091
source "${activate_script}"

if [ "$#" -gt 0 ]; then
  log_info "[activate] Running inside ${venv_dir}: $*"
  exec "$@"
fi

target_shell="${SHELL:-/bin/bash}"
log_info "[activate] Dropping into ${target_shell} with ${venv_dir} activated"
exec "${target_shell}" -i

