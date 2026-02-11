#!/usr/bin/env python
"""Enforce Docker ignore policy: engine-local files only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    ROOT / "docker" / "trt" / ".dockerignore",
    ROOT / "docker" / "vllm" / ".dockerignore",
}

FORBIDDEN = {
    ROOT / ".dockerignore",
}


def _first_effective_line(path: Path) -> str | None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return None


def main() -> int:
    violations: list[str] = []

    discovered = set(ROOT.rglob(".dockerignore"))
    allowed = REQUIRED

    for path in sorted(FORBIDDEN):
        if path.exists():
            rel = path.relative_to(ROOT)
            violations.append(f"  {rel}: root-level .dockerignore is forbidden; use engine-local files only")

    for path in sorted(REQUIRED):
        if not path.exists():
            rel = path.relative_to(ROOT)
            violations.append(f"  {rel}: missing required engine-local .dockerignore")
            continue
        first_line = _first_effective_line(path)
        if first_line != "**":
            rel = path.relative_to(ROOT)
            violations.append(f"  {rel}: first effective rule must be `**` (deny-all default)")

    extras = discovered - allowed - FORBIDDEN
    for path in sorted(extras):
        rel = path.relative_to(ROOT)
        violations.append(f"  {rel}: unexpected .dockerignore (only docker/trt and docker/vllm are allowed)")

    if violations:
        print("Docker ignore policy violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
