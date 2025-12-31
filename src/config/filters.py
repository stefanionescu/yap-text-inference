"""Regex assets shared by text sanitizers and log filters."""

from __future__ import annotations

import re

# ============================================================================
# HUGGINGFACE PROGRESS BAR GROUPS
# ============================================================================

# Download-related progress bar groups in huggingface_hub
HF_DOWNLOAD_GROUPS: tuple[str, ...] = (
    "huggingface_hub.http_get",           # Standard downloads (snapshot_download/hf_hub_download)
    "huggingface_hub.xet_get",            # Xet-accelerated downloads
    "huggingface_hub.snapshot_download",  # Parallel snapshot fetch progress
)

# Upload-related progress bar groups in huggingface_hub
HF_UPLOAD_GROUPS: tuple[str, ...] = (
    "huggingface_hub.lfs_upload",         # LFS file uploads
    "huggingface_hub.hf_file_system",     # HfFileSystem operations
    "huggingface_hub.hf_api",             # HfApi upload methods
)

# All progress bar groups combined
HF_ALL_GROUPS: tuple[str, ...] = HF_DOWNLOAD_GROUPS + HF_UPLOAD_GROUPS


# ============================================================================
# TRTLLM LOG NOISE PATTERNS
# ============================================================================

# Patterns for suppressing TensorRT-LLM and modelopt log noise during quantization
TRTLLM_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\[TensorRT-LLM].*TensorRT LLM version", re.IGNORECASE),
    re.compile(r"`?torch_dtype`?\s*(is\s+)?deprecated", re.IGNORECASE),
    re.compile(r"Registered <class 'transformers\.models\..+'> to _QuantAttention", re.IGNORECASE),
    re.compile(r"Inserted \d+ quantizers", re.IGNORECASE),
    re.compile(r"Caching activation statistics", re.IGNORECASE),
    re.compile(r"Searching .*parameters", re.IGNORECASE),
    re.compile(r"Loading extension modelopt", re.IGNORECASE),
    re.compile(r"Loaded extension modelopt", re.IGNORECASE),
    re.compile(r"current rank:\s*\d+,\s*tp rank:\s*\d+,\s*pp rank:\s*\d+", re.IGNORECASE),
)


# ============================================================================
# TEXT SANITIZATION PATTERNS
# ============================================================================

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]",
    flags=re.UNICODE,
)

EMOTICON_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    r"[:=;8][-^]?[)dDpP(\\]/\\oO]|"
    r":'\\(|"
    r"<3|"
    r":-?\\||"
    r":-?/|"
    r":3(?!\\d)|"
    r";-?\\)|"
    r"\\^\\_\\^|"
    r"T_T|"
    r"¯\\_\\(ツ\\)_/¯"
    r")"
)

ACTION_EMOTE_PATTERN = re.compile(
    r"\*(?:smirks?|winks?|laughs?|smiles?|frowns?|giggles?)\*",
    re.IGNORECASE,
)

FREESTYLE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:freestyle mode\.?|on the screen now:)\s*",
    re.IGNORECASE,
)
ELLIPSIS_PATTERN = re.compile(r"…[ \t]*")
NEWLINE_TOKEN_PATTERN = re.compile(r"\s*(?:\\n|/n|\r?\n)+\s*")
TRAILING_STREAM_UNSTABLE_CHARS = set(" \t\r\n/\\")
ESCAPED_QUOTE_PATTERN = re.compile(r"(?:\\+)([\"'])")
DOUBLE_DOT_SPACE_PATTERN = re.compile(r"\.\.\s*")
EXAGGERATED_OH_PATTERN = re.compile(r"\b[oO][oOhH]+\b")
ELLIPSIS_TRAILING_DOT_PATTERN = re.compile(r"\.\.\.\s*\.")
LETTERS_ONLY_PATTERN = re.compile(r"^[A-Za-z]+$")
DOT_RUN_PATTERN = re.compile(r"\.{2,}")
# Dots separated by spaces like ". . " or ". . ." → single period
SPACED_DOT_RUN_PATTERN = re.compile(r"(?:\.\s+)+\.")

# Prompt/output sanitization patterns
CTRL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
BIDI_CHAR_PATTERN = re.compile(r"[\u202A-\u202E\u2066-\u2069\u200E\u200F\u061C]")
# Only strip space before these punctuation marks (not apostrophe/quote - keep space for opening quotes)
SPACE_BEFORE_PUNCT_PATTERN = re.compile(r"\s+([,?!])")
LEADING_NEWLINE_TOKENS_PATTERN = re.compile(r"^(?:\s*(?:\\n|/n|\r?\n)+\s*)")
COLLAPSE_SPACES_PATTERN = re.compile(r"[ \t]{2,}")
# Strip any whitespace after ellipsis (... followed by spaces → ...)
ELLIPSIS_TRAILING_SPACE_PATTERN = re.compile(r"\.\.\.\s+")
# Replace one or more dashes/hyphens with a single space
DASH_PATTERN = re.compile(r"-+")

# Email detection pattern (comprehensive but not overly strict)
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

__all__ = [
    # HuggingFace progress bar groups
    "HF_DOWNLOAD_GROUPS",
    "HF_UPLOAD_GROUPS",
    "HF_ALL_GROUPS",
    # TRT-LLM log noise patterns
    "TRTLLM_NOISE_PATTERNS",
    # Text sanitization patterns
    "HTML_TAG_PATTERN",
    "EMOJI_PATTERN",
    "EMOTICON_PATTERN",
    "ACTION_EMOTE_PATTERN",
    "FREESTYLE_PREFIX_PATTERN",
    "ELLIPSIS_PATTERN",
    "NEWLINE_TOKEN_PATTERN",
    "TRAILING_STREAM_UNSTABLE_CHARS",
    "ESCAPED_QUOTE_PATTERN",
    "DOUBLE_DOT_SPACE_PATTERN",
    "EXAGGERATED_OH_PATTERN",
    "ELLIPSIS_TRAILING_DOT_PATTERN",
    "DOT_RUN_PATTERN",
    "SPACED_DOT_RUN_PATTERN",
    "LETTERS_ONLY_PATTERN",
    "CTRL_CHAR_PATTERN",
    "BIDI_CHAR_PATTERN",
    "SPACE_BEFORE_PUNCT_PATTERN",
    "LEADING_NEWLINE_TOKENS_PATTERN",
    "COLLAPSE_SPACES_PATTERN",
    "ELLIPSIS_TRAILING_SPACE_PATTERN",
    "DASH_PATTERN",
    "EMAIL_PATTERN",
]

