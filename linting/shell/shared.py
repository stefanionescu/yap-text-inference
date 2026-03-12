"""Shared helpers for custom shell lint rules."""

from __future__ import annotations

from pathlib import Path
from linting.repo import (
    ROOT,
    HOOKS_DIR,
    DOCKER_DIR,
    LINTING_DIR,
    SCRIPTS_DIR,
    rel,
    load_config_doc,
    iter_shell_files,
    require_section,
    require_string,
    require_string_list,
)

_SHELL_RULES = load_config_doc("rules", "shell.toml")
_SHELL_CONFIG_LABEL = "linting/config/rules/shell.toml"
_SHARED_RULES = require_section(_SHELL_RULES, "shared", _SHELL_CONFIG_LABEL)
_SHARED_RULE_LABEL = f"{_SHELL_CONFIG_LABEL} [shared]"

HOOK_ENTRYPOINTS = tuple(
    ROOT / raw_path for raw_path in require_string_list(_SHARED_RULES, "hook_entrypoints", _SHARED_RULE_LABEL)
)
FORCED_ENTRYPOINT_PREFIXES = tuple(
    require_string_list(_SHARED_RULES, "forced_entrypoint_prefixes", _SHARED_RULE_LABEL)
)
NON_ENTRYPOINT_PREFIXES = tuple(require_string_list(_SHARED_RULES, "non_entrypoint_prefixes", _SHARED_RULE_LABEL))
NON_ENTRYPOINT_DOCKER_INFIX = require_string(_SHARED_RULES, "non_entrypoint_docker_infix", _SHARED_RULE_LABEL)
ENTRYPOINT_ROOTS = tuple(require_string_list(_SHARED_RULES, "entrypoint_roots", _SHARED_RULE_LABEL))
_HOOK_ENTRYPOINTS_RESOLVED = {entrypoint.resolve() for entrypoint in HOOK_ENTRYPOINTS if entrypoint.exists()}


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_mode & 0o111 != 0


def iter_all_shell_files() -> list[Path]:
    """Return all tracked shell-like files that custom rules should scan."""
    return iter_shell_files(SCRIPTS_DIR, DOCKER_DIR, HOOKS_DIR, LINTING_DIR, extra_files=list(HOOK_ENTRYPOINTS))


def iter_target_shell_files(raw_paths: list[str] | None = None) -> list[Path]:
    """Return shell files from *raw_paths* or the full repository shell set."""
    if not raw_paths:
        return iter_all_shell_files()

    resolved_files: list[Path] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        resolved = candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
        if resolved.is_file():
            resolved_files.append(resolved)
    unique_files = {path.resolve(): path for path in resolved_files}
    return [unique_files[key] for key in sorted(unique_files)]


def is_entrypoint(path: Path) -> bool:
    """Return True when *path* behaves like a top-level executable script."""
    resolved_path = path.resolve()
    if resolved_path in _HOOK_ENTRYPOINTS_RESOLVED:
        return True

    relative = rel(path)
    if any(relative.startswith(prefix) for prefix in FORCED_ENTRYPOINT_PREFIXES):
        return True
    if any(relative.startswith(prefix) for prefix in NON_ENTRYPOINT_PREFIXES) or (
        relative.startswith("docker/") and NON_ENTRYPOINT_DOCKER_INFIX in relative
    ):
        return False
    if any(relative == root or relative.startswith(f"{root}/") for root in ENTRYPOINT_ROOTS):
        return _is_executable_file(path)
    if relative.startswith("linting/"):
        return _is_executable_file(path)
    return False
