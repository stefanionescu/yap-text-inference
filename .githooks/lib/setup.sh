#!/usr/bin/env bash
# Configure git to use this repository's custom hook directory.

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "${ROOT_DIR}"

git config core.hooksPath .githooks

echo "Git hooks installed."
echo ""
echo "Install/update Bun tooling with: bun install"
echo "Hook helper scripts can then be run with: bun run setup:hooks"
echo ""
echo "Available hook flags:"
echo "  SKIP_HOOKS=1 git commit|push        - Skip all custom hooks"
echo "  SKIP_GITLINT=1 git commit           - Skip conventional commit validation"
echo "  SKIP_COMMITLINT=1 git commit        - Legacy alias for SKIP_GITLINT"
echo "  SKIP_ENV_CHECK=1 git commit         - Skip production env-file guard"
echo "  SKIP_DOCS=1 git commit|push         - Skip markdown, typo, and banned-term checks"
echo "  SKIP_PYTHON=1 git commit|push       - Skip Python lint stages"
echo "  SKIP_CODE=1 git commit|push         - Deprecated alias for SKIP_PYTHON"
echo "  SKIP_SHELL=1 git commit|push        - Skip shell lint stages"
echo "  SKIP_DOCKER=1 git commit|push       - Skip Docker lint stages"
echo "  SKIP_QUALITY=1 git push             - Skip complexity and hygiene checks"
echo "  SKIP_SECURITY_SCANS=1 git push      - Skip security scanners"
echo "  SKIP_TESTS=1 git push               - Skip coverage/test gate"
echo "  SKIP_HOOKS_SELF=1 git commit|push   - Skip hook self-linting"
echo "  RUN_SONAR=1 git push                - Run local SonarQube wrapper during security stage"
