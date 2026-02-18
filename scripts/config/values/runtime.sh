#!/usr/bin/env bash
# =============================================================================
# Runtime Script Configuration Values
# =============================================================================
# Canonical runtime path defaults shared across shell scripts.

# shellcheck disable=SC2034
readonly CFG_RUNTIME_RUN_DIR=".run"
readonly CFG_RUNTIME_LOG_DIR="logs"

# shellcheck disable=SC2034
readonly CFG_RUNTIME_SERVER_PID_FILE="server.pid"
readonly CFG_RUNTIME_SERVER_LOG_FILE="server.log"
readonly CFG_RUNTIME_SERVER_LOG_TRIM_FILE=".server.log.trim"
readonly CFG_RUNTIME_DEPLOYMENT_PID_FILE=".run/deployment.pid"
readonly CFG_RUNTIME_LAST_CONFIG_FILE=".run/last_config.env"
readonly CFG_RUNTIME_TRT_ENGINE_ENV_FILE=".run/trt_engine_dir.env"

# shellcheck disable=SC2034
readonly CFG_RUNTIME_WARMUP_LOCK_FILE=".run/warmup.lock"
readonly CFG_RUNTIME_WARMUP_LOG_FILE="logs/warmup.log"
readonly CFG_RUNTIME_WARMUP_CAPTURE_FILE="logs/warmup.server.log"
