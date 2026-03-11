#!/usr/bin/env bash
# run_codeql_binary - Resolve and exec the CodeQL CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"
source_security_config "codeql"

CODEQL_COMMAND="$(resolve_required_tool_command "${CODEQL_TOOL_NAME}")"
exec "${CODEQL_COMMAND}" "$@"
