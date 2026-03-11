"""Shared utilities for custom structural linters.

Provides common path constants, file iteration, source parsing, and
violation reporting so individual linter modules stay focused on their
single rule.
"""

from __future__ import annotations

import ast
import sys
import tokenize
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
LINTING_CONFIG_DIR = ROOT / "linting" / "config"

_POLICY_PATH = ROOT / "linting" / "policy.toml"
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


# Threshold constants (read from policy.toml, with defaults)
SRC_FILE_LINES: int = int(_limits().get("src_file_lines", 300))  # type: ignore[arg-type]
SHELL_FILE_LINES: int = int(_limits().get("shell_file_lines", 300))  # type: ignore[arg-type]
FUNCTION_LINES: int = int(_limits().get("function_lines", 60))  # type: ignore[arg-type]
MIN_PREFIX_COLLISION: int = int(_limits().get("min_prefix_collision", 2))  # type: ignore[arg-type]
SHELL_FUNCTION_LINES: int = int(_limits().get("shell_function_lines", 100))  # type: ignore[arg-type]


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
    """Return a dict section from ``linting/policy.toml`` or an empty mapping."""
    value = _POLICY.get(name)
    return value if isinstance(value, dict) else {}


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def rel(path: Path) -> str:
    """Return *path* relative to the project root as a string."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def iter_python_files(*dirs: Path) -> list[Path]:
    """Return sorted .py files under *dirs*, skipping ``__pycache__``."""
    files: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for py in sorted(d.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            files.append(py)
    return files


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


def parse_source(filepath: Path) -> tuple[str, ast.Module] | None:
    """Read and parse a Python file, returning ``(source, tree)`` or ``None``."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return None

    return source, tree


def comment_lines(filepath: Path) -> set[int]:
    """Return 1-based line numbers that are comment-only lines."""
    comments: set[int] = set()
    try:
        with filepath.open("rb") as f:
            for tok in tokenize.tokenize(f.readline):
                if tok.type == tokenize.COMMENT:
                    comments.add(tok.start[0])
    except tokenize.TokenError:
        pass
    return comments


def docstring_lines(tree: ast.AST) -> set[int]:
    """Return 1-based line numbers occupied by module/class/function docstrings."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if not getattr(node, "body", None):
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        if not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        for line_no in range(first.lineno, first.end_lineno + 1):
            lines.add(line_no)
    return lines


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
