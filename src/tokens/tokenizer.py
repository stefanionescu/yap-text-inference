"""Fast tokenizer wrapper for token counting and trimming.

This module provides the FastTokenizer class that wraps either:
1. A local tokenizer.json file (fastest, using the tokenizers library)
2. A HuggingFace transformers tokenizer (AutoTokenizer, slower but more compatible)

FastTokenizer provides a unified interface for token counting, trimming, and
encoding. Singleton accessors for chat and tool tokenizers are in the
registry module (src/tokens/registry.py).

Environment Variables:
    TOKENIZERS_PARALLELISM=false: Set automatically to avoid fork warnings
"""

from __future__ import annotations

import logging
import os
from threading import Lock
from typing import Any

# Disable tokenizers parallelism before importing tokenizers (prevents fork warnings)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from tokenizers import Tokenizer

from .loaders import load_local_tokenizer, load_transformers_with_fallback
from .source import inspect_source, resolve_transformers_target

logger = logging.getLogger(__name__)


class FastTokenizer:
    """High-performance tokenizer wrapper for counting and trimming.

    This class provides a unified interface over different tokenizer
    backends (tokenizers library vs transformers). It prefers the
    faster tokenizers library when tokenizer.json is available.

    Thread-safe via internal Lock for all public methods.

    Attributes:
        tok: The tokenizers.Tokenizer instance (if loaded).
        _hf_tok: The transformers tokenizer instance (if loaded).
    """

    def __init__(self, path_or_repo: str, *, load_transformers_tok: bool = True):
        """Create a tokenizer optimized for counting/trimming.

        Args:
            path_or_repo: Local directory or HuggingFace repo id.
            load_transformers_tok: Whether to also load a transformers tokenizer.
        """
        self._lock = Lock()
        self.tok: Tokenizer | None = None
        self._hf_tok = None

        source = inspect_source(path_or_repo)
        local_tok = load_local_tokenizer(source)
        if local_tok:
            self.tok = local_tok

        if not load_transformers_tok:
            if self.tok is None:
                raise RuntimeError(
                    "FastTokenizer requires load_transformers_tok=True when tokenizer.json "
                    f"is missing at {path_or_repo}"
                )
            return

        target = resolve_transformers_target(path_or_repo, source)
        self._hf_tok = load_transformers_with_fallback(
            target=target,
            original_path=path_or_repo,
            source=source,
            have_local=self.tok is not None,
        )

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
            if self.tok is not None:
                enc = self.tok.encode(text)
                try:
                    return enc.n_tokens  # type: ignore[attr-defined]
                except AttributeError:
                    return len(enc.ids)
            # transformers fallback (fast or slow)
            try:
                # Avoid adding special tokens to mirror Tokenizer behavior
                ids = self._hf_tok.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]
            except AttributeError:
                # Some tokenizers prefer the __call__ API
                enc = self._hf_tok(  # type: ignore[call-arg]
                    text,
                    add_special_tokens=False,
                    return_attention_mask=False,
                    return_token_type_ids=False,
                )
                ids = enc["input_ids"] if isinstance(enc, dict) else enc[0]["input_ids"]
            return len(ids)

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
            if self.tok is not None:
                enc = self.tok.encode(text)
                ids = enc.ids
                if len(ids) <= max_tokens:
                    return text
                kept = ids[:max_tokens] if keep == "start" else ids[-max_tokens:]
                return self.tok.decode(kept)

            # transformers fallback (fast or slow)
            try:
                ids = self._hf_tok.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]
            except AttributeError:
                enc = self._hf_tok(  # type: ignore[call-arg]
                    text,
                    add_special_tokens=False,
                    return_attention_mask=False,
                    return_token_type_ids=False,
                )
                ids = enc["input_ids"] if isinstance(enc, dict) else enc[0]["input_ids"]

            if len(ids) <= max_tokens:
                return text
            kept = ids[:max_tokens] if keep == "start" else ids[-max_tokens:]
            # Decode without injecting special tokens or cleaning spaces
            return self._hf_tok.decode(  # type: ignore[attr-defined]
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
            if self.tok is not None:
                return self.tok.encode(text).ids
            try:
                ids = self._hf_tok.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]
            except AttributeError:
                enc = self._hf_tok(  # type: ignore[call-arg]
                    text,
                    add_special_tokens=False,
                    return_attention_mask=False,
                    return_token_type_ids=False,
                )
                ids = enc["input_ids"] if isinstance(enc, dict) else enc[0]["input_ids"]
            return list(ids)

    def get_transformers_tokenizer(self) -> Any:
        """Return the underlying transformers tokenizer if available, None otherwise."""
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
            RuntimeError: If no transformers tokenizer is available or no chat template.
        """
        with self._lock:
            if self._hf_tok is None:
                raise RuntimeError(
                    "apply_chat_template requires a transformers tokenizer, but only tokenizer.json was loaded"
                )
            if not hasattr(self._hf_tok, "apply_chat_template"):
                raise RuntimeError("Tokenizer does not have apply_chat_template method")
            return self._hf_tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=add_generation_prompt,
                **template_kwargs,
            )


__all__ = ["FastTokenizer"]
