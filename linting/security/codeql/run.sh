#!/usr/bin/env bash
# run_codeql - Wrapper for the local CodeQL scan.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/scan.sh"
