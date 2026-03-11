"""PyMarkdown plugin to enforce repo-specific title case for ATX headings."""

from __future__ import annotations

import re
import json
from pathlib import Path
from pymarkdown.tokens.markdown_token import MarkdownToken
from pymarkdown.plugin_manager.rule_plugin import RulePlugin
from pymarkdown.plugin_manager.plugin_scan_context import PluginScanContext
from pymarkdown.plugin_manager.plugin_details import PluginDetails, PluginDetailsV2

_LOWERCASE_WORDS_PATH = Path(__file__).resolve().parents[2] / "config" / "language" / "lowercase-words.json"
_MIN_BRAND_LETTERS = 2
_ATX_HEADING_PATTERN = re.compile(r"^(#{1,6}\s+)(.+)$")
_LEADING_PUNCTUATION_PATTERN = re.compile(r'^([("\'\[]*)(.*)')
_HEADING_TOKENIZER = re.compile(r"(`[^`]+`)|(\s+)|([^\s`]+)")


def _load_lowercase_words() -> list[str]:
    return json.loads(_LOWERCASE_WORDS_PATH.read_text(encoding="utf-8"))


def _tokenize(text: str) -> list[dict[str, str]]:
    tokens: list[dict[str, str]] = []
    for match in _HEADING_TOKENIZER.finditer(text):
        if match.group(1):
            tokens.append({"type": "code", "value": match.group(1)})
        elif match.group(2):
            tokens.append({"type": "separator", "value": match.group(2)})
        else:
            tokens.append({"type": "word", "value": match.group(3)})
    return tokens


def _is_path(word: str) -> bool:
    return word.startswith("/")


def _is_all_caps(word: str) -> bool:
    letters = re.sub(r"[^a-zA-Z]", "", word)
    return len(letters) > 1 and letters == letters.upper()


def _is_mixed_case_brand(word: str) -> bool:
    letters = re.sub(r"[^a-zA-Z]", "", word)
    if len(letters) < _MIN_BRAND_LETTERS:
        return False
    if letters[0] != letters[0].lower():
        return False
    return letters[1:] != letters[1:].lower()


def _capitalize_first(word: str) -> str:
    match = _LEADING_PUNCTUATION_PATTERN.match(word)
    if not match or not match.group(2):
        return word
    return match.group(1) + match.group(2)[0].upper() + match.group(2)[1:]


def _lowercase_first(word: str) -> str:
    match = _LEADING_PUNCTUATION_PATTERN.match(word)
    if not match or not match.group(2):
        return word
    return match.group(1) + match.group(2)[0].lower() + match.group(2)[1:]


def _title_case_word(word: str, should_capitalize: bool) -> str:
    if "-" in word:
        segments = []
        for segment in word.split("-"):
            if _is_all_caps(segment) or _is_mixed_case_brand(segment):
                segments.append(segment)
            else:
                segments.append(_capitalize_first(segment) if should_capitalize else _lowercase_first(segment))
        return "-".join(segments)
    return _capitalize_first(word) if should_capitalize else _lowercase_first(word)


def _should_preserve_word(word: str) -> bool:
    return _is_all_caps(word) or _is_mixed_case_brand(word) or _is_path(word)


def _should_capitalize_word(
    index: int,
    word: str,
    first_word_index: int,
    last_word_index: int,
    lowercase_words: list[str],
) -> bool:
    if index in {first_word_index, last_word_index}:
        return True
    stripped = re.sub(r'^[("\'\[]*', "", word).lower()
    return stripped not in lowercase_words


def _apply_title_case(tokens: list[dict[str, str]], lowercase_words: list[str]) -> str:
    word_indices = [index for index, token in enumerate(tokens) if token["type"] == "word"]
    if not word_indices:
        return "".join(token["value"] for token in tokens)

    first_word_index = word_indices[0]
    last_word_index = word_indices[-1]
    adjusted: list[str] = []

    for index, token in enumerate(tokens):
        if token["type"] != "word":
            adjusted.append(token["value"])
            continue

        word = token["value"]
        if _should_preserve_word(word):
            adjusted.append(word)
            continue

        should_capitalize = _should_capitalize_word(
            index=index,
            word=word,
            first_word_index=first_word_index,
            last_word_index=last_word_index,
            lowercase_words=lowercase_words,
        )
        adjusted.append(_title_case_word(word, should_capitalize))

    return "".join(adjusted)


class HeadingTitleCase(RulePlugin):
    """Enforce title case for ATX headings with repo-specific exceptions."""

    def __init__(self) -> None:
        super().__init__()
        self.__heading_lines: set[int] = set()
        self.__lowercase_words = _load_lowercase_words()

    def get_details(self) -> PluginDetails:
        return PluginDetailsV2(
            plugin_name="heading-title-case",
            plugin_id="YTI101",
            plugin_enabled_by_default=False,
            plugin_description="Headings should use title case",
            plugin_version="1.0.0",
            plugin_url="https://github.com/yap-text-inference",
            plugin_supports_fix=True,
            plugin_fix_level=0,
        )

    def starting_new_file(self) -> None:
        self.__heading_lines = set()

    def next_token(self, context: PluginScanContext, token: MarkdownToken) -> None:
        _ = context
        if token.is_atx_heading:
            self.__heading_lines.add(token.line_number)

    def next_line(self, context: PluginScanContext, line: str) -> None:
        if context.line_number not in self.__heading_lines:
            return

        match = _ATX_HEADING_PATTERN.match(line)
        if not match:
            return

        prefix, heading_text = match.groups()
        corrected_text = _apply_title_case(_tokenize(heading_text), self.__lowercase_words)
        if corrected_text == heading_text:
            return

        corrected_line = f"{prefix}{corrected_text}"
        if context.in_fix_mode:
            context.set_current_fix_line(corrected_line)
            return

        self.report_next_line_error(
            context,
            len(prefix) + 1,
            extra_error_information=f'Expected: "{corrected_line}"',
        )
