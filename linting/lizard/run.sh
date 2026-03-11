#!/usr/bin/env bash
# run_lizard - Run cyclomatic complexity analysis across Python and shell code.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LIZARD_FLAGS=(
  --CCN 10
  --length 60
  --arguments 8
)

if ! command -v lizard >/dev/null 2>&1; then
  echo "error: lizard is not installed" >&2
  exit 1
fi

cd "${REPO_ROOT}"
lizard "${LIZARD_FLAGS[@]}" --whitelist .whitelizard src/ scripts/ docker/ linting/ .githooks/
