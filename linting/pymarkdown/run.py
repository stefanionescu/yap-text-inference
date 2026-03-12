"""Wrapper around pymarkdown with repo-local plugins and path filtering."""

from __future__ import annotations

import sys
import subprocess  # nosec B404
from pathlib import Path, PurePosixPath

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from linting.repo import ROOT, load_config_doc, require_section, require_string_list

CONFIG_FILE = ROOT / ".pymarkdown.toml"
_MIN_CLI_ARGUMENTS = 2

_PYMARKDOWN_CONFIG_LABEL = "linting/config/rules/pymarkdown.toml"
_RUN_RULES = require_section(load_config_doc("rules", "pymarkdown.toml"), "run", _PYMARKDOWN_CONFIG_LABEL)
_RUN_RULE_LABEL = f"{_PYMARKDOWN_CONFIG_LABEL} [run]"
PLUGIN_FILES = tuple(ROOT / raw_path for raw_path in require_string_list(_RUN_RULES, "plugin_files", _RUN_RULE_LABEL))
ENABLED_RULES = require_string_list(_RUN_RULES, "enabled_rules", _RUN_RULE_LABEL)
EXCLUDE_PATTERNS = tuple(require_string_list(_RUN_RULES, "exclude_patterns", _RUN_RULE_LABEL))


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
        ",".join(ENABLED_RULES),
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

    result = subprocess.run(command, check=False, cwd=ROOT)  # noqa: S603  # nosec B603
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
