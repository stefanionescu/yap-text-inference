#!/usr/bin/env bash

# Centralized constants for shell scripts.
# Import this file to access shared configuration values.
# shellcheck disable=SC2034  # Variables are used by sourcing scripts.

# Python version required for TensorRT-LLM engine.
# vLLM works with Python 3.10-3.12, but TRT-LLM 1.2.0rc5 requires 3.10 specifically.
readonly SCRIPTS_TRT_REQUIRED_PYTHON_VERSION="3.10"

# Maximum server log size before trimming (100 MB).
readonly SCRIPTS_MAX_SERVER_LOG_BYTES=$((100 * 1024 * 1024))

# Default connection fallback when MAX_CONCURRENT_CONNECTIONS is not set.
readonly SCRIPTS_WARMUP_DEFAULT_CONN_FALLBACK=8

# Default warmup timeout in seconds.
readonly SCRIPTS_WARMUP_TIMEOUT_SECS_DEFAULT=300

# Default warmup retry count.
readonly SCRIPTS_WARMUP_RETRIES_DEFAULT=1

# Health check polling interval in seconds.
readonly SCRIPTS_WARMUP_HEALTH_POLL_INTERVAL_SECS_DEFAULT=2

# Delay between warmup runs in seconds.
readonly SCRIPTS_WARMUP_RUN_DELAY_SECS_DEFAULT=1

