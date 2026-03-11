"""PyMarkdown plugin to reject double hyphens in Markdown prose."""

from __future__ import annotations

import re
from pymarkdown.plugin_manager.rule_plugin import RulePlugin
from pymarkdown.plugin_manager.plugin_scan_context import PluginScanContext
from pymarkdown.plugin_manager.plugin_details import PluginDetails, PluginDetailsV3

_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_LINK_DESTINATION_RE = re.compile(r"\]\([^)\n]*\)")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?[-:| ]+\|?\s*$")
_HTML_COMMENT_RE = re.compile(r"^\s*<!--.*-->\s*$")


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
        if context.line_number == 1 and stripped == "---":
            self.__in_front_matter = True
            return True
        if not self.__in_front_matter:
            return False
        if stripped == "---":
            self.__in_front_matter = False
        return True

    def _handle_fenced_code(self, stripped: str) -> bool:
        if stripped.startswith("```") or stripped.startswith("~~~"):
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
