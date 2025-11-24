"""Tokenizer access for chat and tool models.

Provides cached tokenizers for each deployed model so counting/trimming always
uses the correct tokenizer (chat vs tool).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

# Disable tokenizers parallelism before importing tokenizers (prevents fork warnings)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from tokenizers import Tokenizer

from ..config import CHAT_MODEL, TOOL_MODEL, DEPLOY_CHAT, DEPLOY_TOOL

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TokenizerSource:
    original_path: str
    is_local: bool
    tokenizer_json_path: str | None
    awq_metadata_model: str | None


@dataclass(slots=True)
class TransformersTarget:
    identifier: str
    local_only: bool


class FastTokenizer:
    def __init__(self, path_or_repo: str):
        """Create a tokenizer optimized for counting/trimming."""
        self._lock = Lock()
        self.tok: Tokenizer | None = None
        self._hf_tok = None  # transformers tokenizer (fast or slow)

        source = self._inspect_source(path_or_repo)
        if self._load_local_tokenizer(source):
            return

        target = self._resolve_transformers_target(path_or_repo, source)
        try:
            self._hf_tok = self._load_transformers_tokenizer(target)
        except Exception:
            if target.identifier != path_or_repo and source.is_local:
                fallback = TransformersTarget(path_or_repo, True)
                self._hf_tok = self._load_transformers_tokenizer(fallback)
                logger.info("tokenizer: fallback load transformers local path=%s", path_or_repo)
            else:
                raise

    def count(self, text: str) -> int:
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
        """Return token ids for the provided text without special tokens."""
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

    def get_transformers_tokenizer(self):
        """Return the underlying transformers tokenizer if available, None otherwise."""
        with self._lock:
            return self._hf_tok

    def _inspect_source(self, path_or_repo: str) -> TokenizerSource:
        try:
            is_local = os.path.exists(path_or_repo)
        except Exception:
            is_local = False

        tokenizer_json_path = os.path.join(path_or_repo, "tokenizer.json") if is_local else None
        awq_metadata_model: str | None = None

        if is_local:
            meta_path = Path(path_or_repo) / "awq_metadata.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    candidate = (meta.get("source_model") or "").strip()
                    if candidate:
                        awq_metadata_model = candidate
                except Exception:
                    pass

        return TokenizerSource(
            original_path=path_or_repo,
            is_local=is_local,
            tokenizer_json_path=tokenizer_json_path,
            awq_metadata_model=awq_metadata_model,
        )

    def _load_local_tokenizer(self, source: TokenizerSource) -> bool:
        tokenizer_path = source.tokenizer_json_path
        if not tokenizer_path or not os.path.isfile(tokenizer_path):
            return False
        self.tok = Tokenizer.from_file(tokenizer_path)
        logger.info("tokenizer: loaded local tokenizer.json at %s", tokenizer_path)
        return True

    def _resolve_transformers_target(
        self,
        path_or_repo: str,
        source: TokenizerSource,
    ) -> TransformersTarget:
        if not source.is_local:
            return TransformersTarget(path_or_repo, False)
        if source.tokenizer_json_path and os.path.isfile(source.tokenizer_json_path):
            return TransformersTarget(path_or_repo, True)
        if source.awq_metadata_model:
            return TransformersTarget(source.awq_metadata_model, False)
        return TransformersTarget(path_or_repo, True)

    def _load_transformers_tokenizer(self, target: TransformersTarget):
        try:
            from transformers import AutoTokenizer  # lazy import
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Transformers is required for tokenizer fallback: {exc}") from exc

        def _try_load(use_fast: bool):
            return AutoTokenizer.from_pretrained(
                target.identifier,
                use_fast=use_fast,
                trust_remote_code=True,
                local_files_only=target.local_only,
            )

        try:
            tokenizer = _try_load(True)
        except Exception:
            tokenizer = _try_load(False)

        logger.info(
            "tokenizer: loaded transformers tokenizer target=%s local_only=%s",
            target.identifier,
            target.local_only,
        )
        return tokenizer


_chat_tok: FastTokenizer | None = None
_tool_tok: FastTokenizer | None = None
_chat_tok_lock = Lock()
_tool_tok_lock = Lock()


def get_chat_tokenizer() -> FastTokenizer:
    if not DEPLOY_CHAT:
        raise RuntimeError("get_chat_tokenizer() called but DEPLOY_CHAT is False")
    global _chat_tok
    if _chat_tok is not None:
        return _chat_tok
    with _chat_tok_lock:
        if _chat_tok is None:
            if not CHAT_MODEL:
                raise ValueError("CHAT_MODEL is required when DEPLOY_CHAT is True")
            _chat_tok = FastTokenizer(CHAT_MODEL)
    return _chat_tok


def get_tool_tokenizer() -> FastTokenizer:
    if not DEPLOY_TOOL:
        raise RuntimeError("get_tool_tokenizer() called but DEPLOY_TOOL is False")
    global _tool_tok
    if _tool_tok is not None:
        return _tool_tok
    with _tool_tok_lock:
        if _tool_tok is None:
            if not TOOL_MODEL:
                raise ValueError("TOOL_MODEL is required when DEPLOY_TOOL is True")
            _tool_tok = FastTokenizer(TOOL_MODEL)
    return _tool_tok
