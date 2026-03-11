#!/usr/bin/env bash
# Configure git to use this repository's custom hook directory.

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "${ROOT_DIR}"

git config core.hooksPath .githooks

echo "Git hooks installed."
echo ""
echo "Install/update Bun tooling with: bun install"
echo "Reinstall hooks anytime with: bash .githooks/lib/setup.sh"
echo "Run full repo maintenance from the top level with: nox -s lint|test|security"
echo ""
echo "Available hook flags:"
echo "  SKIP_HOOKS=1 git commit|push        - Skip all custom hooks"
echo "  SKIP_GITLINT=1 git commit           - Skip conventional commit validation"
echo "  SKIP_COMMITLINT=1 git commit        - Legacy alias for SKIP_GITLINT"
echo "  SKIP_ENV_CHECK=1 git commit         - Skip production env-file guard"
echo "  SKIP_DOCS=1 git commit              - Skip full docs/text linting"
echo "  SKIP_PYTHON=1 git commit            - Skip Python lint stages"
echo "  SKIP_CODE=1 git commit              - Deprecated alias for SKIP_PYTHON"
echo "  SKIP_SHELL=1 git commit             - Skip shell lint stages"
echo "  SKIP_DOCKER=1 git commit            - Skip Docker lint stages"
echo "  SKIP_QUALITY=1 git commit           - Skip complexity and hygiene checks"
echo "  SKIP_SECURITY_SCANS=1 git push      - Skip security scanners"
echo "  ENABLE_TRIVY=1 git push             - Include Trivy during pre-push security scans"
echo "  SKIP_HOOKS_SELF=1 git commit        - Skip hook self-linting"
echo "  RUN_COVERAGE=1 git push             - Enable coverage/test gate"
echo "  RUN_SONAR=1 git push                - Run local SonarQube wrapper during security stage"
