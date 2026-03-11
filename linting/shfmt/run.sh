#!/usr/bin/env bash
# run_shfmt - Resolve and exec the repo-managed shfmt CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../tooling/common.sh
source "${SCRIPT_DIR}/../tooling/common.sh"

SHFMT_COMMAND="$(resolve_required_tool_command "shfmt")"
exec "${SHFMT_COMMAND}" "$@"
