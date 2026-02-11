"""Regex assets shared by text sanitizers and log filters."""

from __future__ import annotations

import re

# ============================================================================
# HUGGINGFACE PROGRESS BAR GROUPS
# ============================================================================

# Download-related progress bar groups in huggingface_hub
HF_DOWNLOAD_GROUPS: tuple[str, ...] = (
    "huggingface_hub.http_get",  # Standard downloads (snapshot_download/hf_hub_download)
    "huggingface_hub.xet_get",  # Xet-accelerated downloads
    "huggingface_hub.snapshot_download",  # Parallel snapshot fetch progress
)

# Upload-related progress bar groups in huggingface_hub
HF_UPLOAD_GROUPS: tuple[str, ...] = (
    "huggingface_hub.lfs_upload",  # LFS file uploads
    "huggingface_hub.hf_file_system",  # HfFileSystem operations
    "huggingface_hub.hf_api",  # HfApi upload methods
)

# All progress bar groups combined
HF_ALL_GROUPS: tuple[str, ...] = HF_DOWNLOAD_GROUPS + HF_UPLOAD_GROUPS


# ============================================================================
# TRTLLM LOG NOISE PATTERNS
# ============================================================================

# Patterns for suppressing TensorRT-LLM and modelopt log noise during quantization
# and engine initialization. TRT-LLM emits verbose logs directly to stdout/stderr.
TRTLLM_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # === Quantization-related noise ===
    re.compile(r"\[TensorRT-LLM].*TensorRT LLM version", re.IGNORECASE),
    re.compile(r"Registered <class 'transformers\.models\..+'> to _QuantAttention", re.IGNORECASE),
    re.compile(r"Inserted \d+ quantizers", re.IGNORECASE),
    re.compile(r"Caching activation statistics", re.IGNORECASE),
    re.compile(r"Searching .*parameters", re.IGNORECASE),
    re.compile(r"Loading extension modelopt", re.IGNORECASE),
    re.compile(r"Loaded extension modelopt", re.IGNORECASE),
    re.compile(r"current rank:\s*\d+,\s*tp rank:\s*\d+,\s*pp rank:\s*\d+", re.IGNORECASE),
    # === Engine initialization noise ===
    # Dated TRT-LLM logs: [01/01/2026-17:31:12] [TRT-LLM] [I/W] message
    re.compile(r"^\[\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\]\s*\[TRT-LLM\]\s*\[[IWE]\]"),
    # Bracketed TensorRT-LLM logs: [TensorRT-LLM][INFO/WARNING] message
    re.compile(r"^\[TensorRT-LLM\]\[(?:INFO|WARNING|ERROR)\]"),
    # Python version warnings from tensorrt_llm modules
    re.compile(r"Current Python version.*below the recommended", re.IGNORECASE),
    re.compile(r"upgrade to Python.*for the best experience", re.IGNORECASE),
    # Implicitly setting config warnings
    re.compile(r"Implicitly setting \w+Config\.\w+", re.IGNORECASE),
    # Set PluginConfig messages
    re.compile(r"Set PluginConfig\.\w+ to", re.IGNORECASE),
    # MPI session messages
    re.compile(r"rank \d+ using MpiPoolSession", re.IGNORECASE),
    re.compile(r"Refreshed the MPI local session", re.IGNORECASE),
    re.compile(r"MPI size:\s*\d+.*rank:\s*\d+", re.IGNORECASE),
    re.compile(r"Rank \d+ is using GPU \d+", re.IGNORECASE),
    # Package distribution warnings
    re.compile(r"Multiple distributions found for package", re.IGNORECASE),
    # trust_remote_code warning from tokenizers
    re.compile(r"The argument `?trust_remote_code`? is to be used with Auto classes", re.IGNORECASE),
    # Build config ignored warning
    re.compile(r"The build_config is ignored for model format", re.IGNORECASE),
    # TRTGptModel config lines
    re.compile(r"TRTGptModel\s+\w+:", re.IGNORECASE),
    # Engine loading/inspection messages
    re.compile(r"Loaded engine size:", re.IGNORECASE),
    re.compile(r"Engine load time", re.IGNORECASE),
    re.compile(r"Engine version.*found in the config file", re.IGNORECASE),
    re.compile(r"Inspecting the engine to identify potential runtime issues", re.IGNORECASE),
    re.compile(r"The profiling verbosity of the engine", re.IGNORECASE),
    re.compile(r"Using an engine plan file across different models", re.IGNORECASE),
    # Memory usage changes
    re.compile(r"\[MemUsageChange\]", re.IGNORECASE),
    re.compile(r"Memory usage when calculating max tokens", re.IGNORECASE),
    # KV cache and block allocation
    re.compile(r"Blocks per window size:", re.IGNORECASE),
    re.compile(r"Max KV cache blocks per sequence:", re.IGNORECASE),
    re.compile(r"Number of tokens per block:", re.IGNORECASE),
    re.compile(r"Allocated.*for max tokens in paged KV cache", re.IGNORECASE),
    # Scheduler/feature messages
    re.compile(r"Capacity Scheduler Policy:", re.IGNORECASE),
    re.compile(r"Context Chunking Scheduler Policy:", re.IGNORECASE),
    re.compile(r"CacheTransceiver is disabled", re.IGNORECASE),
    # Gather logits settings
    re.compile(r"gatherContextLogits:", re.IGNORECASE),
    re.compile(r"gatherGenerationLogits:", re.IGNORECASE),
    # Using user-specified devices
    re.compile(r"Using user-specified devices:", re.IGNORECASE),
    # LLM backend selection
    re.compile(r"Using LLM with TensorRT backend", re.IGNORECASE),
    re.compile(r"Using default gpus_per_node:", re.IGNORECASE),
    # === Application TRT startup logs ===
    # Python logging format: INFO YYYY-MM-DD HH:MM:SS,mmm [module:line] message
    # Suppress verbose startup logs from src.engines.trt.* modules
    re.compile(r"^INFO\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}\s+\[src\.engines\.trt\.(setup|engine):\d+\]"),
    # Warmup logs specifically for TRT-LLM
    re.compile(
        r"^INFO\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}\s+\[src\.engines\.warmup:\d+\].*TRT-LLM",
        re.IGNORECASE,
    ),
    # Cache daemon message about TRT block reuse
    re.compile(r"cache reset daemon:.*TRT-LLM", re.IGNORECASE),
)


# ============================================================================
# VLLM LOG NOISE PATTERNS
# ============================================================================

# Patterns for suppressing vLLM engine initialization noise.
# These match vLLM's bracketed log format and worker process output.
VLLM_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # vLLM bracketed log format: INFO 12-31 19:07:25 [model.py:514] message
    re.compile(r"^(?:INFO|WARNING|DEBUG)\s+\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\[[\w.]+:\d+\]"),
    # Worker process prefixed logs: (EngineCore_DP0 pid=60611) INFO/WARNING ...
    re.compile(r"^\(EngineCore_\w+\s+pid=\d+\)\s+(?:INFO|WARNING|DEBUG)\s+\d{2}-\d{2}"),
    # CUDA graph capturing progress bars
    re.compile(r"Capturing CUDA graphs.*\d+%", re.IGNORECASE),
    # Safetensors/checkpoint loading progress bars
    re.compile(r"Loading safetensors checkpoint shards:\s*\d+%", re.IGNORECASE),
    # Empty worker process line (just prefix with no content)
    re.compile(r"^\(EngineCore_\w+\s+pid=\d+\)\s*$"),
    # trust_remote_code warning from transformers
    re.compile(r"The argument `?trust_remote_code`? is to be used with Auto classes", re.IGNORECASE),
    # Multiple distributions warning (pip/packaging)
    re.compile(r"Multiple distributions found for package", re.IGNORECASE),
    # === Application vLLM startup logs ===
    # Python logging format: INFO YYYY-MM-DD HH:MM:SS,mmm [module:line] message
    # Suppress verbose startup logs from src.engines.vllm.* modules
    re.compile(
        r"^INFO\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}\s+\[src\.engines\.vllm\.(engine|cache_daemon|setup|create|args|tokenizer|memory|factory):\d+\]"
    ),
    # Suppress verbose startup logs from src.quantization.vllm.* modules
    re.compile(r"^INFO\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}\s+\[src\.quantization\.vllm\.[\w.]+:\d+\]"),
    # Cache daemon started message
    re.compile(r"cache reset daemon started", re.IGNORECASE),
)


# ============================================================================
# TOOL CLASSIFIER LOG NOISE PATTERNS
# ============================================================================

# Patterns for suppressing tool classifier warmup and dependency install noise.
# These match pip output and classifier initialization logs during tool deployment.
TOOL_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Classifier ready logs from src.classifier.adapter
    re.compile(r"^INFO\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}\s+\[src\.classifier\.adapter:\d+\]"),
    # pip install output lines
    re.compile(
        r"^(?:Requirement already satisfied|Collecting|Downloading"
        r"|Installing collected packages|Successfully installed)",
        re.IGNORECASE,
    ),
    re.compile(r"^\s+(?:Downloading|Using cached)\s+\S+\.whl", re.IGNORECASE),
    re.compile(r"^\s+Attempting uninstall:", re.IGNORECASE),
    re.compile(r"^\s+Found existing installation:", re.IGNORECASE),
    re.compile(r"^\s+Uninstalling \S+:", re.IGNORECASE),
    re.compile(r"^\s+Successfully uninstalled", re.IGNORECASE),
    re.compile(r"^Looking in indexes:", re.IGNORECASE),
)


# ============================================================================
# LLMCOMPRESSOR LOG NOISE PATTERNS
# ============================================================================

# Patterns for suppressing llmcompressor/AutoAWQ calibration progress output.
# These match tqdm-style progress bars emitted during quantization calibration.
LLMCOMPRESSOR_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Checkpoint loading progress bars
    re.compile(r"Loading checkpoint shards:\s*\d+%", re.IGNORECASE),
    # Dataset generation/preprocessing progress bars
    re.compile(r"Generating \w+ split:\s*\d+%", re.IGNORECASE),
    re.compile(r"Preprocessing:\s*\d+%", re.IGNORECASE),
    re.compile(r"Tokenizing:\s*\d+%", re.IGNORECASE),
    # Calibration/quantization progress bars (with layer counter prefix or standalone)
    re.compile(r"\(\d+/\d+\):\s*Calibrating:\s*\d+%", re.IGNORECASE),
    re.compile(r"\(\d+/\d+\):\s*Propagating:\s*\d+%", re.IGNORECASE),
    # tqdm iteration format: "Smoothing: 0it", "Calibrating weights: 280it"
    re.compile(r"Smoothing:\s*\d+", re.IGNORECASE),
    re.compile(r"Calibrating weights:\s*\d+", re.IGNORECASE),
    # Tokenizer regex warning from Mistral models
    re.compile(r"tokenizer.*incorrect regex pattern.*fix_mistral_regex", re.IGNORECASE),
    # llmcompressor timestamp logs: 2026-01-12T16:08:24.565859+0000 | module | INFO -
    re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{4}\s*\|.*\|\s*(?:INFO|WARNING)\s*-"),
)


# ============================================================================
# TEXT SANITIZATION PATTERNS
# ============================================================================

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

EMOJI_PATTERN = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"
    "\U0001f300-\U0001f5ff"
    "\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff"
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\u2600-\u26ff"
    "\u2700-\u27bf"
    "]",
    flags=re.UNICODE,
)

EMOTICON_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"[:=;8][-^]?[)dDpP(/\\oO]|"  # Basic: :) :D :P :O :( :/ :\ and variants
    r":'\(|"  # Crying: :'(
    r"<3|"  # Heart
    r":-?\||"  # Neutral: :| :-|
    r":-?/|"  # Uncertain: :/ :-/
    r":3(?!\d)|"  # Cat face :3 (not :30 time)
    r";-?[)pPdD]|"  # Wink variants: ;) ;P ;D ;-) ;-P
    r"\^_\^|"  # Japanese happy
    r"T_T|"  # Crying
    r"[xX][dD](?![a-zA-Z])|"  # XD xD
    r"\(?\u256F\u00B0\u25A1\u00B0\)?\u256F\uFE35\s*\u253B\u2501\u253B"  # Table flip
    r")",
    re.IGNORECASE,
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
# Match 4+ dots to collapse to ellipsis (preserve 3-dot ellipsis "...")
DOT_RUN_PATTERN = re.compile(r"\.{4,}")
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
# Emdash variants: -- or actual em/en-dash unicode characters → space
EMDASH_PATTERN = re.compile(r"--+|—|–")
# Math subtraction: digit - digit with spaces on both sides (avoids phone numbers like 555-1234)
SUBTRACTION_PATTERN = re.compile(r"(\d)\s+-\s+(\d)")
# Negative number: dash immediately before digit, not preceded by word char
NEGATIVE_NUMBER_PATTERN = re.compile(r"(?<!\w)-(\d)")
# Single-letter suffix hyphen: word-X (where X is single letter) → join without space
# e.g., "vintage-y" → "vintagey", "80-s" → "80s"
SINGLE_LETTER_SUFFIX_PATTERN = re.compile(r"(\w)-([A-Za-z])(?![A-Za-z])")
# Word hyphen: letter-letter (compound words) → space
WORD_HYPHEN_PATTERN = re.compile(r"([A-Za-z])-([A-Za-z])")

# Temperature units with degree symbol
TEMP_FAHRENHEIT_PATTERN = re.compile(r"°\s*F\b", re.IGNORECASE)
TEMP_CELSIUS_PATTERN = re.compile(r"°\s*C\b", re.IGNORECASE)
TEMP_KELVIN_PATTERN = re.compile(r"°\s*K\b", re.IGNORECASE)
# Standalone degree symbol (not followed by F/C/K)
DEGREE_SYMBOL_PATTERN = re.compile(r"°(?!\s*[FCK])", re.IGNORECASE)

# Percent sign
PERCENT_PATTERN = re.compile(r"%")

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
    # vLLM log noise patterns
    "VLLM_NOISE_PATTERNS",
    # Tool classifier log noise patterns
    "TOOL_NOISE_PATTERNS",
    # LLMCompressor log noise patterns
    "LLMCOMPRESSOR_NOISE_PATTERNS",
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
    "EMDASH_PATTERN",
    "SUBTRACTION_PATTERN",
    "NEGATIVE_NUMBER_PATTERN",
    "SINGLE_LETTER_SUFFIX_PATTERN",
    "WORD_HYPHEN_PATTERN",
    "TEMP_FAHRENHEIT_PATTERN",
    "TEMP_CELSIUS_PATTERN",
    "TEMP_KELVIN_PATTERN",
    "DEGREE_SYMBOL_PATTERN",
    "PERCENT_PATTERN",
    "EMAIL_PATTERN",
]
