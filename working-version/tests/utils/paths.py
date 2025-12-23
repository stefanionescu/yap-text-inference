from __future__ import annotations

from pathlib import Path

from tests.config.paths import AUDIO_SUBDIR_NAME  # noqa: E402

# Repository root (two levels up from this file: tests/utils -> tests -> root)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Common output directory used by test scripts
AUDIO_DIR = ROOT_DIR / AUDIO_SUBDIR_NAME
