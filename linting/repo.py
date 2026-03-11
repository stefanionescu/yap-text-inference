"""Repository-scoped helpers shared across custom linting code."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
LINTING_CONFIG_DIR = ROOT / "linting" / "config"

_POLICY_PATH = LINTING_CONFIG_DIR / "repo" / "policy.toml"
_CONFIG_CACHE: dict[Path, dict[str, object]] = {}

# ---------------------------------------------------------------------------
# Policy config
# ---------------------------------------------------------------------------


def _load_policy() -> dict[str, object]:
    if not _POLICY_PATH.exists():
        return {}
    try:
        return tomllib.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


_POLICY: dict[str, object] = _load_policy()


def load_config_doc(*relative_parts: str) -> dict[str, object]:
    """Load a TOML config document under ``linting/config`` or return an empty dict."""
    config_path = LINTING_CONFIG_DIR.joinpath(*relative_parts)
    cached = _CONFIG_CACHE.get(config_path)
    if cached is not None:
        return cached
    if not config_path.exists():
        _CONFIG_CACHE[config_path] = {}
        return {}
    try:
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    _CONFIG_CACHE[config_path] = loaded
    return loaded


def _limits() -> dict[str, object]:
    val = _POLICY.get("limits")
    return val if isinstance(val, dict) else {}


def _paths() -> dict[str, object]:
    val = _POLICY.get("paths")
    return val if isinstance(val, dict) else {}


_REPO_PATHS = load_config_doc("repo", "paths.toml")


def _int_config_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


# Threshold constants (read from policy.toml, with defaults)
SRC_FILE_LINES = _int_config_value(_limits().get("src_file_lines", 300), 300)
SHELL_FILE_LINES = _int_config_value(_limits().get("shell_file_lines", 300), 300)
FUNCTION_LINES = _int_config_value(_limits().get("function_lines", 60), 60)
MIN_PREFIX_COLLISION = _int_config_value(_limits().get("min_prefix_collision", 2), 2)
SHELL_FUNCTION_LINES = _int_config_value(_limits().get("shell_function_lines", 100), 100)


def _repo_path(name: str, default: str) -> Path:
    value = _REPO_PATHS.get(name)
    if isinstance(value, str):
        return ROOT / value
    fallback = _paths().get(name, default)
    return ROOT / str(fallback)


# Directory constants (read from linting/config/repo/paths.toml with policy.toml fallback)
SRC_DIR: Path = _repo_path("src", "src")
TESTS_DIR: Path = _repo_path("tests", "tests")
CONFIG_DIR: Path = _repo_path("config", "src/config")
SCRIPTS_DIR: Path = _repo_path("scripts", "scripts")
DOCKER_DIR: Path = _repo_path("docker", "docker")
HOOKS_DIR: Path = _repo_path("hooks", ".githooks")
LINTING_DIR: Path = _repo_path("linting", "linting")


def policy_section(name: str) -> dict[str, object]:
    """Return a dict section from ``linting/config/repo/policy.toml`` or an empty mapping."""
    value = _POLICY.get(name)
    return value if isinstance(value, dict) else {}


def string_list(value: object) -> list[str]:
    """Return only the string entries from *value* when it is a list."""
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, str)]


def rel(path: Path) -> str:
    """Return *path* relative to the project root as a string."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def iter_shell_files(*dirs: Path, include_hook_entrypoints: bool = False) -> list[Path]:
    """Return sorted shell files under *dirs* plus optional hook entrypoints."""
    files: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for sh_file in sorted(d.rglob("*.sh")):
            if "__pycache__" in sh_file.parts:
                continue
            files.append(sh_file)

    if include_hook_entrypoints:
        for relative in ("pre-commit", "pre-push", "commit-msg"):
            candidate = HOOKS_DIR / relative
            if candidate.is_file():
                files.append(candidate)

    unique_files = {path.resolve(): path for path in files}
    return [unique_files[key] for key in sorted(unique_files)]


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def report(header: str, violations: list[str]) -> int:
    """Print *violations* to stderr under *header* and return an exit code."""
    if not violations:
        return 0
    print(f"{header}:", file=sys.stderr)
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1
