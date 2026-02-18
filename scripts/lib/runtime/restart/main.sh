#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Restart Guard Utilities
# =============================================================================
# Entry point for restart guard helpers split into focused modules.

_RUNTIME_GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../cleanup/main.sh
source "${_RUNTIME_GUARD_DIR}/../cleanup/main.sh"
# shellcheck source=../../../config/values/core.sh
source "${_RUNTIME_GUARD_DIR}/../../../config/values/core.sh"
# shellcheck source=../../../config/patterns.sh
source "${_RUNTIME_GUARD_DIR}/../../../config/patterns.sh"

# Restart guard modules
# shellcheck source=io.sh
source "${_RUNTIME_GUARD_DIR}/io.sh"
# shellcheck source=engine_switch.sh
source "${_RUNTIME_GUARD_DIR}/engine_switch.sh"
# shellcheck source=snapshot.sh
source "${_RUNTIME_GUARD_DIR}/snapshot.sh"
