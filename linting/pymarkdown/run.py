"""Wrapper around pymarkdown with repo-local plugins and path filtering."""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path, PurePosixPath

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / ".pymarkdown.toml"
RULE_CONFIG_FILE = ROOT / "linting" / "config" / "rules" / "pymarkdown.toml"
_MIN_CLI_ARGUMENTS = 2
PLUGIN_FILES = (
    ROOT / "linting" / "pymarkdown" / "rules" / "no_banned_terms.py",
    ROOT / "linting" / "pymarkdown" / "rules" / "heading_title_case.py",
    ROOT / "linting" / "pymarkdown" / "rules" / "no_double_hyphen.py",
)


def _load_rule_config() -> dict[str, object]:
    if not RULE_CONFIG_FILE.exists():
        return {}
    try:
        loaded = tomllib.loads(RULE_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


_RULES = _load_rule_config()
_RUN_RULES = _RULES.get("run")
if not isinstance(_RUN_RULES, dict):
    _RUN_RULES = {}
EXCLUDE_PATTERNS = tuple(str(value) for value in _RUN_RULES.get("exclude_patterns", []) if isinstance(value, str)) or (
    "node_modules/**",
    ".git/**",
    ".cache/**",
    ".venv/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    "linting/.tools/**",
    "coverage/**",
    "htmlcov/**",
    "rules/**",
    "src/quantization/**/readme/*.md",
)


def _relative_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _is_markdown_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".md"


def _is_excluded(path: Path) -> bool:
    relative = PurePosixPath(_relative_posix(path))
    return any(relative.match(pattern) for pattern in EXCLUDE_PATTERNS)


def _iter_selected_paths(raw_paths: list[str]) -> list[str]:
    selected: list[str] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        candidate = path if path.is_absolute() else (Path.cwd() / path)
        resolved = candidate.resolve()
        if not _is_markdown_file(resolved) or _is_excluded(resolved):
            continue
        selected.append(_relative_posix(resolved))
    return sorted(dict.fromkeys(selected))


def main() -> int:
    if len(sys.argv) < _MIN_CLI_ARGUMENTS or sys.argv[1] not in {"scan", "fix"}:
        print("usage: python linting/pymarkdown/run.py [scan|fix] [path ...]", file=sys.stderr)
        return 2

    mode = sys.argv[1]
    explicit_paths = _iter_selected_paths(sys.argv[2:])

    command = [
        "pymarkdown",
        "--config",
        str(CONFIG_FILE),
        "--strict-config",
        "--disable-rules",
        "*",
        "--enable-rules",
        "YTI100,YTI101,YTI102",
    ]
    for plugin_file in PLUGIN_FILES:
        command.extend(["--add-plugin", str(plugin_file)])
    command.append(mode)

    if explicit_paths:
        command.extend(explicit_paths)
    else:
        command.append("--recurse")
        for pattern in EXCLUDE_PATTERNS:
            command.extend(["--exclude", pattern])
        command.append(str(ROOT))

    result = subprocess.run(command, check=False, cwd=ROOT)  # noqa: S603
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
