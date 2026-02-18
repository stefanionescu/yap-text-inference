#!/usr/bin/env bash
# =============================================================================
# Script Regex / Pattern Configuration
# =============================================================================
# Shared validation patterns and canonical option labels.

# shellcheck disable=SC2034
readonly CFG_PATTERN_NON_NEGATIVE_INT='^[0-9]+$'
readonly CFG_PATTERN_POSITIVE_INT='^[1-9][0-9]*$'
readonly CFG_PATTERN_BINARY_FLAG='^[01]$'

# shellcheck disable=SC2034
readonly CFG_DEPLOY_MODE_BOTH="both"
readonly CFG_DEPLOY_MODE_CHAT="chat"
readonly CFG_DEPLOY_MODE_TOOL="tool"
readonly CFG_ENGINE_TRT="trt"
readonly CFG_ENGINE_VLLM="vllm"
