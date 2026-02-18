#!/usr/bin/env bash
# shellcheck disable=SC2034
# =============================================================================
# Script Regex / Pattern Configuration
# =============================================================================
# Shared validation patterns and canonical option labels.
[[ -n ${_CFG_PATTERNS_LOADED:-} ]] && return 0
_CFG_PATTERNS_LOADED=1

readonly CFG_PATTERN_NON_NEGATIVE_INT='^[0-9]+$'
readonly CFG_PATTERN_POSITIVE_INT='^[1-9][0-9]*$'
readonly CFG_PATTERN_BINARY_FLAG='^[01]$'
readonly CFG_PATTERN_QWEN_MOE_SUFFIX='-a[0-9]+b'

readonly CFG_DEPLOY_MODE_BOTH="both"
readonly CFG_DEPLOY_MODE_CHAT="chat"
readonly CFG_DEPLOY_MODE_TOOL="tool"
readonly CFG_ENGINE_TRT="trt"
readonly CFG_ENGINE_VLLM="vllm"
