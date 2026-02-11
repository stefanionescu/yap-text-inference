#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Virtual Environment Management
# =============================================================================
# Aggregates venv helper modules for runtime/path resolution and venv lifecycle.

_VENV_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Base dependencies used by all venv helper modules.
# shellcheck source=./pip.sh
source "${_VENV_HELPERS_DIR}/pip.sh"
# shellcheck source=../common/constants.sh
source "${_VENV_HELPERS_DIR}/../common/constants.sh"

# Runtime/python-selection/path helpers.
# shellcheck source=./venv_runtime.sh
source "${_VENV_HELPERS_DIR}/venv_runtime.sh"

# Virtualenv create/repair/activation helpers.
# shellcheck source=./venv_create.sh
source "${_VENV_HELPERS_DIR}/venv_create.sh"
