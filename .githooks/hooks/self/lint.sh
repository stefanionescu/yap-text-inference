#!/usr/bin/env bash
# Hook self-lint checks for .githooks shell scripts.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper for hook file collection -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"
# shellcheck disable=SC1091  # lint:justify -- reason: hook self-checks use the repo-managed Python and tool bootstrap -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/bootstrap.sh"

cd "${ROOT_DIR}"
collect_hook_files_array
if skip_when_no_files; then
  exit 0
fi

shellcheck -x -e SC1091 "${FILES[@]}"
python -m linting.shell.run "${FILES[@]}"
