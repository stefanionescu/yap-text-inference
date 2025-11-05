"""Tokenizer access for chat and tool models.

Provides cached tokenizers for each deployed model so counting/trimming always
uses the correct tokenizer (chat vs tool).
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from threading import Lock
import logging
from typing import Optional

from tokenizers import Tokenizer

from ..config import CHAT_MODEL, TOOL_MODEL

logger = logging.getLogger(__name__)


class FastTokenizer:
    def __init__(self, path_or_repo: str):
        """Create a tokenizer optimized for counting/trimming.

        Behavior:
        - If `tokenizer.json` exists at `path_or_repo`, use `tokenizers.Tokenizer`.
        - Otherwise, fall back to `transformers.AutoTokenizer` (fast preferred,
          slow if fast is unavailable). This avoids treating local paths as
          Hugging Face repo IDs.
        """

        self._lock = Lock()
        self.tok: Optional[Tokenizer] = None
        self._hf_tok = None  # transformers tokenizer (fast or slow)

        is_local = False
        try:
            is_local = os.path.exists(path_or_repo)
        except Exception:
            is_local = False

        tokenizer_json_path = os.path.join(path_or_repo, "tokenizer.json") if is_local else None

        # Detect AWQ output directory to optionally use original source model's tokenizer
        awq_metadata_model: Optional[str] = None
        if is_local:
            meta_path = Path(path_or_repo) / "awq_metadata.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    candidate = (meta.get("source_model") or "").strip()
                    if candidate:
                        awq_metadata_model = candidate
                except Exception:
                    awq_metadata_model = None

        if is_local and tokenizer_json_path and os.path.isfile(tokenizer_json_path):
            # Fast path: local folder with tokenizer.json — load directly from file
            # Using from_file avoids any Hugging Face Hub repo-id validation for local paths
            self.tok = Tokenizer.from_file(tokenizer_json_path)
            logger.info(f"tokenizer: loaded local tokenizer.json at {tokenizer_json_path}")
            return

        # Fallback: rely on Transformers. Prefer fast; fallback to slow if needed.
        try:
            from transformers import AutoTokenizer  # lazy import
        except Exception as exc:  # pragma: no cover - transformers is a hard dep in this project
            raise RuntimeError(f"Transformers is required for tokenizer fallback: {exc}")

        # Strategy:
        # - If this is a local AWQ dir, force local-only loading to avoid Hub calls.
        # - If local loading fails (missing tokenizer files), try original source model from metadata.
        # - Else, use provided identifier as-is.

        load_target = path_or_repo
        use_local_only = is_local

        # If AWQ metadata is present, prefer using the original source model for tokenizer
        # when the local dir lacks tokenizer files.
        if is_local and not (tokenizer_json_path and os.path.isfile(tokenizer_json_path)):
            if awq_metadata_model:
                load_target = awq_metadata_model
                use_local_only = False  # allow Hub for the original model tokenizer

        # Helper to attempt loading with a given setting; prefer fast
        def _try_load(target: str, local_only: bool):
            # Transformers honors local_files_only to avoid any Hub calls
            try:
                return AutoTokenizer.from_pretrained(
                    target,
                    use_fast=True,
                    trust_remote_code=True,
                    local_files_only=local_only,
                )
            except Exception:
                return AutoTokenizer.from_pretrained(
                    target,
                    use_fast=False,
                    trust_remote_code=True,
                    local_files_only=local_only,
                )

        try:
            self._hf_tok = _try_load(load_target, use_local_only)
            logger.info(f"tokenizer: loaded transformers tokenizer target={load_target} local_only={use_local_only}")
            return
        except Exception:
            # Final fallback: if we tried metadata and failed, try the original path without Hub
            if load_target != path_or_repo and is_local:
                self._hf_tok = _try_load(path_or_repo, local_only=True)
                logger.info(f"tokenizer: fallback load transformers local path={path_or_repo}")
                return
            raise

    def count(self, text: str) -> int:
        if not text:
            return 0
        with self._lock:
            if self.tok is not None:
                return self.tok.encode(text).num_tokens
            # transformers fallback (fast or slow)
            try:
                # Avoid adding special tokens to mirror Tokenizer behavior
                ids = self._hf_tok.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]
            except AttributeError:
                # Some tokenizers prefer the __call__ API
                enc = self._hf_tok(text, add_special_tokens=False, return_attention_mask=False, return_token_type_ids=False)  # type: ignore[call-arg]
                ids = enc["input_ids"] if isinstance(enc, dict) else enc[0]["input_ids"]
            return len(ids)

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
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
                enc = self._hf_tok(text, add_special_tokens=False, return_attention_mask=False, return_token_type_ids=False)  # type: ignore[call-arg]
                ids = enc["input_ids"] if isinstance(enc, dict) else enc[0]["input_ids"]

            if len(ids) <= max_tokens:
                return text
            kept = ids[:max_tokens] if keep == "start" else ids[-max_tokens:]
            # Decode without injecting special tokens or cleaning spaces
            return self._hf_tok.decode(kept, skip_special_tokens=True, clean_up_tokenization_spaces=False)  # type: ignore[attr-defined]


_chat_tok: Optional[FastTokenizer] = None
_tool_tok: Optional[FastTokenizer] = None
_chat_tok_lock = Lock()
_tool_tok_lock = Lock()


def get_chat_tokenizer() -> FastTokenizer:
    global _chat_tok
    if _chat_tok is not None:
        return _chat_tok
    with _chat_tok_lock:
        if _chat_tok is None:
            _chat_tok = FastTokenizer(CHAT_MODEL)
    return _chat_tok


def get_tool_tokenizer() -> FastTokenizer:
    global _tool_tok
    if _tool_tok is not None:
        return _tool_tok
    with _tool_tok_lock:
        if _tool_tok is None:
            _tool_tok = FastTokenizer(TOOL_MODEL)
    return _tool_tok


