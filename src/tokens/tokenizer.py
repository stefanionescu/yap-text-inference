"""Tokenizer wrapper for token counting and trimming.

This module provides the FastTokenizer class as a thin wrapper around
``transformers.AutoTokenizer`` only. Runtime-configured accessors for chat and
tool tokenizers are in the registry module (src/tokens/registry.py).
"""

from __future__ import annotations

import os
from typing import Any
from threading import Lock

# Disable tokenizers parallelism before importing transformers/tokenizers.
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from transformers import AutoTokenizer


class FastTokenizer:
    """Thread-safe wrapper around a single transformers tokenizer instance."""

    def __init__(self, path_or_repo: str):
        """Create a tokenizer for counting/trimming from local path or HF repo."""
        self._lock = Lock()
        self._hf_tok = AutoTokenizer.from_pretrained(
            path_or_repo,
            trust_remote_code=True,
            local_files_only=os.path.exists(path_or_repo),
        )

    def _encode_ids_locked(self, text: str) -> list[int]:
        """Encode text without special tokens.

        Must be called while holding ``self._lock``.
        """
        enc = self._hf_tok(
            text,
            add_special_tokens=False,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        input_ids = enc["input_ids"] if isinstance(enc, dict) else enc.input_ids
        if input_ids and isinstance(input_ids[0], list):
            input_ids = input_ids[0]
        return list(input_ids)

    def count(self, text: str) -> int:
        """Count the number of tokens in the text.

        Args:
            text: Text to tokenize and count.

        Returns:
            Number of tokens in the text.
        """
        if not text:
            return 0
        with self._lock:
            return len(self._encode_ids_locked(text))

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
        """Trim text to fit within max_tokens.

        Args:
            text: Text to trim.
            max_tokens: Maximum number of tokens to keep.
            keep: Which part to keep - "start" or "end".

        Returns:
            Trimmed text fitting within max_tokens.
        """
        if max_tokens <= 0 or not text:
            return ""
        with self._lock:
            ids = self._encode_ids_locked(text)
            if len(ids) <= max_tokens:
                return text
            kept = ids[:max_tokens] if keep == "start" else ids[-max_tokens:]
            return self._hf_tok.decode(
                kept,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )

    def encode_ids(self, text: str) -> list[int]:
        """Return token ids for the provided text without special tokens.

        Args:
            text: Text to encode.

        Returns:
            List of token IDs.
        """
        if not text:
            return []
        with self._lock:
            return self._encode_ids_locked(text)

    def get_transformers_tokenizer(self) -> Any:
        """Return the underlying transformers tokenizer."""
        with self._lock:
            return self._hf_tok

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        add_generation_prompt: bool = True,
        **template_kwargs: Any,
    ) -> str:
        """Apply the tokenizer's built-in chat template to format messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                      Roles are typically 'system', 'user', 'assistant'.
            add_generation_prompt: If True, appends the assistant turn start token.
            **template_kwargs: Additional kwargs passed to apply_chat_template.

        Returns:
            Formatted prompt string ready for generation.

        Raises:
            RuntimeError: If tokenizer has no chat template support.
        """
        with self._lock:
            if not hasattr(self._hf_tok, "apply_chat_template"):
                raise RuntimeError("Tokenizer does not have apply_chat_template method")
            return self._hf_tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=add_generation_prompt,
                **template_kwargs,
            )


__all__ = ["FastTokenizer"]
