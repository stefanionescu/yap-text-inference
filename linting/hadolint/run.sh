#!/usr/bin/env bash
# run_hadolint - Resolve and exec the repo-managed hadolint CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../tooling/common.sh
source "${SCRIPT_DIR}/../tooling/common.sh"

HADOLINT_COMMAND="$(resolve_required_tool_command "hadolint")"
exec "${HADOLINT_COMMAND}" "$@"
