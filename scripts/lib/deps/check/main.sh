#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Dependency Version Checking Utilities
# =============================================================================
# Entry point for TRT dependency checks. Sources focused check modules.

_DEPS_CHECK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../config/values/trt.sh
source "${_DEPS_CHECK_DIR}/../../../config/values/trt.sh"

# Load shared FlashInfer helper
# shellcheck source=../../env/flashinfer.sh
source "${_DEPS_CHECK_DIR}/../../env/flashinfer.sh"

# Focused check modules
# shellcheck source=python_packages.sh
source "${_DEPS_CHECK_DIR}/python_packages.sh"
# shellcheck source=requirements.sh
source "${_DEPS_CHECK_DIR}/requirements.sh"
# shellcheck source=status.sh
source "${_DEPS_CHECK_DIR}/status.sh"
