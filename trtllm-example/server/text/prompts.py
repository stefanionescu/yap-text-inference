"""Prompt building and chunking utilities for the streaming TTS pipeline."""

from __future__ import annotations

import re

from server.config import settings
from server.config.text import ABBREVIATIONS, ABBREVIATIONS_EN
from server.voices import resolve_voice

PROMPT_PREFIX = "<custom_token_3><|begin_of_text|>"
PROMPT_SUFFIX = "<|eot_id|><custom_token_4><custom_token_5><custom_token_1>"

# Sentence boundary at end-of-string check
__all__ = ["build_prompt", "chunk_by_sentences"]


def build_prompt(text: str, voice: str = "tara") -> str:
    """Return the Orpheus priming prompt for the supplied text and voice."""
    # Accept internal names directly; resolve only external aliases
    internal_names = set(getattr(settings, "internal_voice_names", ()))
    if not internal_names and hasattr(settings, "streaming"):
        internal_names = set(getattr(settings.streaming, "internal_voice_names", ()))
    resolved_voice = voice if voice in internal_names else resolve_voice(voice)
    return f"{PROMPT_PREFIX}{resolved_voice}: {text}{PROMPT_SUFFIX}"


def chunk_by_sentences(text: str, language: str = "en") -> list[str]:
    """
    Split text into sentences only (no word-based chunking).

    This mirrors production behavior where each client message maps to a
    sentence-level generation.
    """
    sentences = _split_sentences(text, language=language)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _split_sentences(text: str, language: str = "en") -> list[str]:
    """
    Split text into sentences using reliable logic:
    - Splits on sentence-ending punctuation (. ! ?)
    - Doesn't split on apostrophes in contractions
    - Handles quotes properly (including French « »)
    - Skips abbreviations (language-specific)
    - Handles French spacing before punctuation (! ? : ;)
    """
    if not text:
        return []

    lang = language.lower() if language else "en"
    abbreviations = ABBREVIATIONS.get(lang, ABBREVIATIONS_EN)
    is_french = lang.startswith("fr")

    sentences: list[str] = []
    current: str = ""
    i = 0

    while i < len(text):
        char = text[i]
        current += char

        if char in ".!?":
            j = i + 1
            while j < len(text) and text[j] in " \t\n\"'”')\\]]»":
                j += 1

            is_sentence_end = False
            if j >= len(text):
                is_sentence_end = True
            elif text[j].isupper() or (is_french and text[j] in "«"):
                search_text = current.rstrip()
                if is_french and i > 0 and text[i - 1] == " ":
                    search_text = current[:-2].rstrip()

                word_match = re.search(r"(\w+)\.?\s*$", search_text)
                if word_match:
                    word = word_match.group(1).lower().rstrip(".")
                    if word not in abbreviations:
                        is_sentence_end = True
                else:
                    is_sentence_end = True

            if is_sentence_end:
                sentence = current.rstrip() if is_french and i > 0 and text[i - 1] == " " else current.strip()

                if sentence and any(ch.isalnum() for ch in sentence):
                    sentences.append(sentence)
                current = ""
                i = j - 1

        i += 1

    if current.strip():
        sentences.append(current.strip())

    return sentences
