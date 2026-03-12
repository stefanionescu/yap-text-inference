#!/usr/bin/env bash
# Hook self-quality checks for duplicate shell fragments in .githooks.
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

python -m linting.python.structure.prefix_collisions .githooks
python -m linting.python.structure.single_file_folders .githooks
bash linting/jscpd/run.sh --config "${HOOK_SELF_JSCPD_CONFIG}"
