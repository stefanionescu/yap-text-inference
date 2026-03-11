#!/usr/bin/env bash
# run_coverage - Generate src-only unit-test coverage and junit XML.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "${ROOT_DIR}"

python -m pytest \
  --cov=src \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --junitxml=pytest.xml \
  tests
