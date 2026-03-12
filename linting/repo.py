"""Repository-scoped helpers shared across custom linting code."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
LINTING_CONFIG_DIR = ROOT / "linting" / "config"

_POLICY_PATH = LINTING_CONFIG_DIR / "repo" / "policy.toml"
_REPO_PATHS_PATH = LINTING_CONFIG_DIR / "repo" / "paths.toml"
_CONFIG_CACHE: dict[Path, dict[str, object]] = {}
_POLICY_LABEL = "linting/config/repo/policy.toml"
_PATHS_LABEL = "linting/config/repo/paths.toml"


def _load_toml_doc(path: Path) -> dict[str, object]:
    cached = _CONFIG_CACHE.get(path)
    if cached is not None:
        return cached
    if not path.exists():
        _CONFIG_CACHE[path] = {}
        return {}
    try:
        loaded = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    _CONFIG_CACHE[path] = loaded
    return loaded


def _dict_section(doc: dict[str, object], name: str) -> dict[str, object]:
    section = doc.get(name)
    return section if isinstance(section, dict) else {}


def config_error(config_label: str, message: str) -> NoReturn:
    raise RuntimeError(f"{config_label}: {message}")


def require_section(doc: dict[str, object], name: str, config_label: str) -> dict[str, object]:
    section = doc.get(name)
    if not isinstance(section, dict):
        config_error(config_label, f"`{name}` must be a table")
    return section


def _int_config_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def require_int(doc: dict[str, object], name: str, config_label: str) -> int:
    parsed = _int_config_value(doc.get(name))
    if parsed is None:
        config_error(config_label, f"`{name}` must be an integer")
    return parsed


def require_string(doc: dict[str, object], name: str, config_label: str) -> str:
    value = doc.get(name)
    if not isinstance(value, str):
        config_error(config_label, f"`{name}` must be a string")
    return value


def require_string_list(doc: dict[str, object], name: str, config_label: str) -> list[str]:
    value = doc.get(name)
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        config_error(config_label, f"`{name}` must be a list of strings")
    return [entry for entry in value if isinstance(entry, str)]


_POLICY: dict[str, object] = _load_toml_doc(_POLICY_PATH)
_POLICY_LIMITS = _dict_section(_POLICY, "limits")
_REPO_PATH_OVERRIDES = _load_toml_doc(_REPO_PATHS_PATH)


def _limit(name: str) -> int:
    return require_int(_POLICY_LIMITS, name, f"{_POLICY_LABEL} [limits]")


def _repo_path(name: str) -> Path:
    value = _REPO_PATH_OVERRIDES.get(name)
    if isinstance(value, str):
        return ROOT / value
    config_error(_PATHS_LABEL, f"`{name}` must be configured as a string path")


# Threshold constants (read from policy.toml, with defaults)
SRC_FILE_LINES = _limit("src_file_lines")
SHELL_FILE_LINES = _limit("shell_file_lines")
FUNCTION_LINES = _limit("function_lines")
MIN_PREFIX_COLLISION = _limit("min_prefix_collision")
SHELL_FUNCTION_LINES = _limit("shell_function_lines")


# Directory constants (read from linting/config/repo/paths.toml)
SRC_DIR: Path = _repo_path("src")
TESTS_DIR: Path = _repo_path("tests")
CONFIG_DIR: Path = _repo_path("config")
SCRIPTS_DIR: Path = _repo_path("scripts")
DOCKER_DIR: Path = _repo_path("docker")
HOOKS_DIR: Path = _repo_path("hooks")
LINTING_DIR: Path = _repo_path("linting")


def load_config_doc(*relative_parts: str) -> dict[str, object]:
    """Load a TOML config document under ``linting/config`` or return an empty dict."""
    return _load_toml_doc(LINTING_CONFIG_DIR.joinpath(*relative_parts))


def policy_section(name: str) -> dict[str, object]:
    """Return a dict section from ``linting/config/repo/policy.toml`` or an empty mapping."""
    return _dict_section(_POLICY, name)


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


def iter_shell_files(*dirs: Path, extra_files: list[Path] | tuple[Path, ...] | None = None) -> list[Path]:
    """Return sorted shell files under *dirs* plus optional extra shell-like files."""
    files: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for sh_file in sorted(d.rglob("*.sh")):
            if "__pycache__" in sh_file.parts:
                continue
            files.append(sh_file)

    for candidate in extra_files or ():
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
