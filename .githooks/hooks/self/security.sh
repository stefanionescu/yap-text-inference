#!/usr/bin/env bash
# Hook self-security checks for bash anti-patterns inside .githooks.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper for hook file collection -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"
# shellcheck disable=SC1091  # lint:justify -- reason: hook self-checks use the repo-managed Python and tool environment -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/env.sh"

cd "${ROOT_DIR}"
collect_hook_files_array
if skip_when_no_files; then
  exit 0
fi

semgrep_args=(--config "${HOOK_SELF_SEMGREP_CONFIG}")
for hook_file in "${FILES[@]}"; do
  semgrep_args+=(--target "${hook_file}")
done
bash linting/semgrep/run.sh "${semgrep_args[@]}"
