#!/usr/bin/env bash
# shellcheck disable=SC2034
# =============================================================================
# Core Script Configuration Values
# =============================================================================
# Canonical defaults shared across shell scripts.
[[ -n ${_CFG_CORE_LOADED:-} ]] && return 0
_CFG_CORE_LOADED=1

readonly CFG_DEFAULT_DEPLOY_MODE="chat"
readonly CFG_DEFAULT_ENGINE="trt"
readonly CFG_DEFAULT_RUNTIME_ENGINE="trt"

readonly CFG_MAX_SERVER_LOG_BYTES=$((100 * 1024 * 1024))
readonly CFG_WARMUP_DEFAULT_CONN_FALLBACK="8"
readonly CFG_WARMUP_TIMEOUT_SECS_DEFAULT="300"
readonly CFG_WARMUP_RETRIES_DEFAULT="1"
readonly CFG_WARMUP_HEALTH_POLL_INTERVAL_SECS_DEFAULT="2"
readonly CFG_WARMUP_RUN_DELAY_SECS_DEFAULT="1"
readonly CFG_WARMUP_DEFAULT_PERSONA_PRIMARY="female"
readonly CFG_WARMUP_DEFAULT_PERSONA_SECONDARY="male"

readonly CFG_SERVER_DEFAULT_CLIENT_HOST="127.0.0.1"
readonly CFG_SERVER_DEFAULT_BIND_HOST="0.0.0.0"
readonly CFG_SERVER_DEFAULT_PORT="8000"

readonly CFG_STOP_DEFAULT_FULL_CLEANUP="1"
readonly CFG_STOP_DEFAULT_HARD_RESET="0"
