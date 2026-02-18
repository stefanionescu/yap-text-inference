#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Virtual Environment Management
# =============================================================================
# Aggregates venv helper modules for runtime/path resolution and venv lifecycle.

_VENV_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Base dependencies used by all venv helper modules.
# shellcheck source=../pip.sh
source "${_VENV_HELPERS_DIR}/../pip.sh"
# shellcheck source=../../../config/values/trt.sh
source "${_VENV_HELPERS_DIR}/../../../config/values/trt.sh"

# Runtime/python-selection/path helpers.
# shellcheck source=./runtime.sh
source "${_VENV_HELPERS_DIR}/runtime.sh"

# Virtualenv create/repair/activation helpers.
# shellcheck source=./create.sh
source "${_VENV_HELPERS_DIR}/create.sh"
