#!/usr/bin/env python3
"""Verify Python filenames use single-word stems."""

from __future__ import annotations

import pathlib
import subprocess
import sys


def is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    try:
        output = subprocess.check_output(
            ["git", "-C", str(repo_root), "ls-files", "*.py"],
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[checknames] failed to list files: {exc}", file=sys.stderr)
        return 2

    bad: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        rel = pathlib.Path(line)
        stem = rel.stem
        if "_" in stem and not is_dunder(stem):
            bad.append(line)

    if bad:
        print("[checknames] filenames must be single-word (no underscores):", file=sys.stderr)
        for entry in bad:
            print(f"  - {entry}", file=sys.stderr)
        return 1

    print("[checknames] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
