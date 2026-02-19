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

_POLICY_PATH = ROOT / "linting" / "policy.toml"

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


def _limits() -> dict[str, object]:
    val = _POLICY.get("limits")
    return val if isinstance(val, dict) else {}


def _paths() -> dict[str, object]:
    val = _POLICY.get("paths")
    return val if isinstance(val, dict) else {}


# Threshold constants (read from policy.toml, with defaults)
SRC_FILE_LINES: int = int(_limits().get("src_file_lines", 300))  # type: ignore[arg-type]
SHELL_FILE_LINES: int = int(_limits().get("shell_file_lines", 300))  # type: ignore[arg-type]
FUNCTION_LINES: int = int(_limits().get("function_lines", 60))  # type: ignore[arg-type]
MIN_PREFIX_COLLISION: int = int(_limits().get("min_prefix_collision", 2))  # type: ignore[arg-type]

# Directory constants (read from policy.toml, with defaults)
SRC_DIR: Path = ROOT / str(_paths().get("src", "src"))
TESTS_DIR: Path = ROOT / str(_paths().get("tests", "tests"))
CONFIG_DIR: Path = ROOT / str(_paths().get("config", "src/config"))

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
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
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
