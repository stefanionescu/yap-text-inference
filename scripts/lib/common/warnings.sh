#!/usr/bin/env bash

# Backwards-compatible shim that sources the centralized noise helpers.

_COMMON_WARNINGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../noise/python.sh
source "${_COMMON_WARNINGS_DIR}/../noise/python.sh"
