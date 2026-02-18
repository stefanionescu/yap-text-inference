#!/usr/bin/env bash
# shellcheck disable=SC2034
# =============================================================================
# Model Detection Configuration Values
# =============================================================================
# Canonical model detection tokens used by shell scripts.
[[ -n ${_CFG_MODEL_LOADED:-} ]] && return 0
_CFG_MODEL_LOADED=1

readonly CFG_MODEL_TOKEN_AWQ="awq"
readonly CFG_MODEL_TOKEN_GPTQ="gptq"
readonly CFG_MODEL_TOKEN_GPTQ_MARLIN="gptq_marlin"

readonly CFG_MODEL_TOKEN_W4A16="w4a16"
readonly CFG_MODEL_TOKEN_COMPRESSED_TENSORS="compressed-tensors"
readonly CFG_MODEL_TOKEN_AUTOROUND="autoround"

readonly CFG_MODEL_TOKEN_TRT="trt"
readonly CFG_MODEL_TOKEN_FP8="fp8"
readonly CFG_MODEL_TOKEN_INT8="int8"
readonly CFG_MODEL_TOKEN_INT8_DASHED="int-8"
readonly CFG_MODEL_TOKEN_8BIT="8bit"
readonly CFG_MODEL_TOKEN_8BIT_DASHED="8-bit"

readonly CFG_MODEL_TRT_KIND_AWQ="trt_awq"
readonly CFG_MODEL_TRT_KIND_FP8="trt_fp8"
readonly CFG_MODEL_TRT_KIND_INT8="trt_int8"
readonly CFG_MODEL_TRT_KIND_8BIT="trt_8bit"
readonly CFG_MODEL_TRT_KIND_MOE="moe"

readonly CFG_MODEL_TOKEN_MOE="moe"
readonly CFG_MODEL_TOKEN_MIXTRAL="mixtral"
readonly CFG_MODEL_TOKEN_DEEPSEEK_V2="deepseek-v2"
readonly CFG_MODEL_TOKEN_DEEPSEEK_V3="deepseek-v3"
readonly CFG_MODEL_TOKEN_ERNIE_45="ernie-4.5"
