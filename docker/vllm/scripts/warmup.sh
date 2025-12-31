#!/usr/bin/env bash
# vLLM-specific warmup wrapper.
#
# Delegates to the shared warmup script with the vLLM engine prefix.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_DIR="${SCRIPT_DIR}/../../common/scripts"

exec "${COMMON_DIR}/warmup.sh" "vllm"
