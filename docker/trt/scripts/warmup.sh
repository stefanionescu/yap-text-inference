#!/usr/bin/env bash
# TRT-specific warmup wrapper.
#
# Delegates to the shared warmup script with the TRT engine prefix.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_DIR="${SCRIPT_DIR}/../../common/scripts"

exec "${COMMON_DIR}/warmup.sh" "trt"
