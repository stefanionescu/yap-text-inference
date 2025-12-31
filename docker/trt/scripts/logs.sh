#!/usr/bin/env bash
# TRT logging - sources shared logging utilities.
#
# This wrapper exists so runtime scripts can source logs.sh from the same
# directory without knowing about the common/ layout.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../common/scripts/logs.sh"
