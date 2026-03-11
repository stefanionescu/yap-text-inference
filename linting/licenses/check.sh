#!/usr/bin/env bash
# run_license_audit - Check installed licenses for repo dependency roots and their transitive dependencies.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
cd "${ROOT_DIR}"

python linting/licenses/check.py
