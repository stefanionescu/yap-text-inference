"""Sampling defaults for chat models.

This module defines the default sampling parameters used during text
generation. These control the randomness and diversity of outputs.

Sampling Parameters:
    temperature: Controls randomness (0=deterministic, 1=more random)
        Higher values produce more creative but less coherent outputs.
    
    top_p (nucleus sampling): Cumulative probability threshold
        Only considers tokens whose cumulative probability <= top_p.
        Lower values (0.8-0.95) reduce unlikely token selection.
    
    top_k: Maximum number of tokens to consider
        0 = disabled, 30-50 is common for chat applications.
    
    min_p: Minimum probability threshold
        Filters out tokens below this probability. Good for avoiding
        very unlikely tokens without being as restrictive as top_k.
    
    repetition_penalty: Penalty for repeating tokens (1.0 = no penalty)
        Values > 1.0 reduce repetition, 1.05-1.15 is typical.
    
    presence_penalty: Penalty for tokens already in context
        Encourages talking about new topics.
    
    frequency_penalty: Penalty based on token frequency in context
        Reduces repetition of the same words/phrases.

Stop Sequences:
    INFERENCE_STOP contains tokens that terminate generation. These are
    model-specific and cover various chat formats (ChatML, Gemma, Kimi, etc.)

All values can be overridden via environment variables or per-request.
"""

import os

from ..helpers.sampling import build_logit_bias_map


# ============================================================================
# Default Sampling Parameters
# ============================================================================
# These are server defaults. Clients can override per-request within limits.

CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", "0.8"))
CHAT_TOP_P = float(os.getenv("CHAT_TOP_P", "0.95"))
CHAT_TOP_K = int(os.getenv("CHAT_TOP_K", "30"))
CHAT_MIN_P = float(os.getenv("CHAT_MIN_P", "0"))
CHAT_REPETITION_PENALTY = float(os.getenv("CHAT_REPETITION_PENALTY", "1.0"))
CHAT_PRESENCE_PENALTY = float(os.getenv("CHAT_PRESENCE_PENALTY", "0"))
CHAT_FREQUENCY_PENALTY = float(os.getenv("CHAT_FREQUENCY_PENALTY", "0"))


# ============================================================================
# Logit Bias (Token Suppression)
# ============================================================================
# Discourage certain tokens/text patterns from being generated.
# -100 effectively bans the token entirely.
# This helps avoid unwanted punctuation, filler words, and expressions.

_DEFAULT_LOGIT_BIAS = {
    "*": -100,      # Markdown emphasis
    "(": -100,      # Parenthetical asides
    ")": -100,
    "~": -100,      # Tildes
    " - ": -100,    # Dashes
    "-": -100,
    "Mmh": -100,    # Filler sounds
    "hmm": -100,
    "…": -100,      # Ellipsis
    "Damn": -100,   # Profanity
    "stud": -100,   # Unwanted terms
}

# ============================================================================
# Stop Sequences
# ============================================================================
# Tokens that terminate generation. Covers multiple chat formats:
# - ChatML: <|im_end|>, <|assistant|>, <|user|>
# - Gemma 1/2: <end_of_turn>, <start_of_turn>
# - Gemma 3: <|eot_id|>, <|start_header_id|>
# - Kimi: <|im_user|>, <|im_system|>, [EOS], [EOT]
# - DeepSeek V2/V3: Fullwidth vertical bars and "User:" prefix

INFERENCE_STOP = [
    # ChatML format
    "<|im_end|>",
    "|im_end|>",
    "<|im_start|>",
    "<|im_start|",
    "<|assistant|>",
    "<|user|>",
    "<|end|>",
    # Gemma 1/2 format
    "<end_of_turn>",
    "<start_of_turn>",
    # Gemma 3 format
    "<|eot_id|>",
    "<|start_header_id|>",
    # Kimi / Kimi Linear format
    "<|im_user|>",
    "<|im_system|>",
    "[EOS]",
    "[EOT]",
    # DeepSeek V2/V3 format (uses fullwidth vertical bars)
    "<｜end▁of▁sentence｜>",
    "<｜begin▁of▁sentence｜>",
    "User:",  # DeepSeek uses "User:" prefix
    # General
    "[SYSTEM_PROMPT]",
    "[/SYSTEM_PROMPT]",
]

CHAT_LOGIT_BIAS = build_logit_bias_map(_DEFAULT_LOGIT_BIAS)


__all__ = [
    "CHAT_TEMPERATURE",
    "CHAT_TOP_P",
    "CHAT_TOP_K",
    "CHAT_MIN_P",
    "CHAT_REPETITION_PENALTY",
    "CHAT_PRESENCE_PENALTY",
    "CHAT_FREQUENCY_PENALTY",
    "INFERENCE_STOP",
    "CHAT_LOGIT_BIAS",
]

