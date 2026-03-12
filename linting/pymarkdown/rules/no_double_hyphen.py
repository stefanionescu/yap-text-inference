"""PyMarkdown plugin to reject double hyphens in Markdown prose."""

from __future__ import annotations

import re
from pathlib import Path
from pymarkdown.plugin_manager.rule_plugin import RulePlugin
from pymarkdown.plugin_manager.plugin_scan_context import PluginScanContext
from pymarkdown.plugin_manager.plugin_details import PluginDetails, PluginDetailsV3

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "rules" / "pymarkdown.toml"
_CONFIG_LABEL = "linting/config/rules/pymarkdown.toml"


def _load_rule_config() -> dict[str, object]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        loaded = tomllib.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _require_section(doc: dict[str, object], name: str) -> dict[str, object]:
    value = doc.get(name)
    if not isinstance(value, dict):
        raise RuntimeError(f"{_CONFIG_LABEL}: `{name}` must be a table")
    return value


def _require_string(doc: dict[str, object], name: str, label: str) -> str:
    value = doc.get(name)
    if not isinstance(value, str):
        raise RuntimeError(f"{label}: `{name}` must be a string")
    return value


def _require_string_list(doc: dict[str, object], name: str, label: str) -> list[str]:
    value = doc.get(name)
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise RuntimeError(f"{label}: `{name}` must be a list of strings")
    return [entry for entry in value if isinstance(entry, str)]


_RULES = _load_rule_config()
_NO_DOUBLE_HYPHEN_RULE = _require_section(_RULES, "no_double_hyphen")
_RULE_LABEL = f"{_CONFIG_LABEL} [no_double_hyphen]"
_INLINE_CODE_RE = re.compile(_require_string(_NO_DOUBLE_HYPHEN_RULE, "inline_code_pattern", _RULE_LABEL))
_LINK_DESTINATION_RE = re.compile(_require_string(_NO_DOUBLE_HYPHEN_RULE, "link_destination_pattern", _RULE_LABEL))
_TABLE_SEPARATOR_RE = re.compile(_require_string(_NO_DOUBLE_HYPHEN_RULE, "table_separator_pattern", _RULE_LABEL))
_HTML_COMMENT_RE = re.compile(_require_string(_NO_DOUBLE_HYPHEN_RULE, "html_comment_pattern", _RULE_LABEL))
_FRONT_MATTER_DELIMITER = _require_string(_NO_DOUBLE_HYPHEN_RULE, "front_matter_delimiter", _RULE_LABEL)
_FENCE_MARKERS = tuple(_require_string_list(_NO_DOUBLE_HYPHEN_RULE, "fence_markers", _RULE_LABEL))


def _strip_inline_code(line: str) -> str:
    return _INLINE_CODE_RE.sub(lambda match: " " * len(match.group(0)), line)


def _strip_link_destinations(line: str) -> str:
    return _LINK_DESTINATION_RE.sub(lambda match: "]" + (" " * (len(match.group(0)) - 1)), line)


class NoDoubleHyphen(RulePlugin):
    """Disallow `--` in markdown prose outside front matter and fenced code blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.__in_front_matter = False
        self.__in_fenced_code = False

    def get_details(self) -> PluginDetails:
        return PluginDetailsV3(
            plugin_name="no-double-hyphen",
            plugin_id="YTI102",
            plugin_enabled_by_default=False,
            plugin_description="Disallow double hyphens in markdown prose",
            plugin_version="1.0.0",
            plugin_url="https://github.com/yap-text-inference",
        )

    def starting_new_file(self) -> None:
        self.__in_front_matter = False
        self.__in_fenced_code = False

    def _handle_front_matter(self, context: PluginScanContext, stripped: str) -> bool:
        if context.line_number == 1 and stripped == _FRONT_MATTER_DELIMITER:
            self.__in_front_matter = True
            return True
        if not self.__in_front_matter:
            return False
        if stripped == _FRONT_MATTER_DELIMITER:
            self.__in_front_matter = False
        return True

    def _handle_fenced_code(self, stripped: str) -> bool:
        if any(stripped.startswith(marker) for marker in _FENCE_MARKERS):
            self.__in_fenced_code = not self.__in_fenced_code
            return True
        return self.__in_fenced_code

    def _should_skip_line(self, stripped: str) -> bool:
        return bool(_TABLE_SEPARATOR_RE.match(stripped) or _HTML_COMMENT_RE.match(stripped))

    def _double_hyphen_column(self, line: str) -> int:
        sanitized = _strip_link_destinations(_strip_inline_code(line))
        return sanitized.find("--")

    def next_line(self, context: PluginScanContext, line: str) -> None:
        stripped = line.strip()
        if self._handle_front_matter(context, stripped):
            return
        if self._handle_fenced_code(stripped) or self._should_skip_line(stripped):
            return
        column = self._double_hyphen_column(line)
        if column == -1:
            return

        self.report_next_line_error(
            context,
            column + 1,
            extra_error_information='double hyphen "--" is not allowed; use an em dash or rephrase',
        )
