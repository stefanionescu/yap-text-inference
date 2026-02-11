#!/usr/bin/env bash
# =============================================================================
# Script Validation Configuration
# =============================================================================
# Canonical defaults for script-side model validation.

# shellcheck disable=SC2034  # consumed by scripts that source this config
readonly VALIDATE_DEFAULT_DEPLOY_MODE="both"
readonly VALIDATE_DEFAULT_ENGINE="trt"
