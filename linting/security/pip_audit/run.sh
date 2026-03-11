#!/usr/bin/env bash
# run_pip_audit - Audit each pinned requirements file independently.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
# shellcheck source=../common.sh
source "${SCRIPT_DIR}/../common.sh"

cd "${REPO_ROOT}"

requirement_files=()
while IFS= read -r requirement_file; do
  [[ -n ${requirement_file} ]] || continue
  requirement_files+=("${requirement_file}")
done < <(
  python - <<'PY'
from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

root = Path.cwd()
doc = tomllib.loads((root / "linting/config/repo/files.toml").read_text(encoding="utf-8"))
for value in doc.get("requirement_files", []):
    if isinstance(value, str):
        print(value)
PY
)

for requirement_file in "${requirement_files[@]}"; do
  python -m pip_audit \
    --disable-pip \
    --no-deps \
    --progress-spinner off \
    --requirement "${requirement_file}"
done
