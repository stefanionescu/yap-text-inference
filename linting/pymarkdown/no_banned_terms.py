"""PyMarkdown plugin to reject banned terms in Markdown content."""

from __future__ import annotations

import re
import json
from pathlib import Path
from pymarkdown.plugin_manager.rule_plugin import RulePlugin
from pymarkdown.plugin_manager.plugin_scan_context import PluginScanContext
from pymarkdown.plugin_manager.plugin_details import PluginDetails, PluginDetailsV3

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "language" / "banned-terms.json"


def _escape_regex(value: str) -> str:
    return re.escape(value)


def _load_terms_regex() -> re.Pattern[str]:
    parsed = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    terms = parsed.get("bannedTerms", [])
    normalized = [str(term).strip().lower() for term in terms if str(term).strip()]
    alternation = "|".join(sorted((_escape_regex(term) for term in normalized), key=len, reverse=True))
    flags = re.IGNORECASE if parsed.get("matching", {}).get("caseInsensitive", False) else 0
    return re.compile(rf"\b(?:{alternation})\b", flags)


class NoBannedTerms(RulePlugin):
    """Disallow configured banned terms in Markdown lines."""

    def __init__(self) -> None:
        super().__init__()
        self.__terms_regex = _load_terms_regex()

    def get_details(self) -> PluginDetails:
        return PluginDetailsV3(
            plugin_name="no-banned-terms",
            plugin_id="YTI100",
            plugin_enabled_by_default=False,
            plugin_description="Disallow banned terms in markdown content",
            plugin_version="1.0.0",
            plugin_url="https://github.com/yap-text-inference",
        )

    def next_line(self, context: PluginScanContext, line: str) -> None:
        match = self.__terms_regex.search(line)
        if not match:
            return
        self.report_next_line_error(
            context,
            match.start() + 1,
            extra_error_information=f'banned term "{match.group(0).lower()}" is not allowed',
        )
