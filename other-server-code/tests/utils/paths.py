from __future__ import annotations

from pathlib import Path

# Repository root (two levels up from this file: tests/utils -> tests -> root)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Common output directory used by test scripts
AUDIO_DIR = ROOT_DIR / "audio"
