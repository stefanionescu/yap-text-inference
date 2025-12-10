"""Classifier-based tool adapter for screenshot intent detection.

This module provides a tool adapter that uses a transformers classifier model
(AutoModelForSequenceClassification) instead of an autoregressive LLM for
tool call detection. This is much faster and lighter than running a full LLM.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.config import CLASSIFIER_MAX_LENGTH

if TYPE_CHECKING:
    from transformers import PreTrainedModel, PreTrainedTokenizerFast

logger = logging.getLogger(__name__)


class ClassifierToolAdapter:
    """Tool adapter using a transformers classifier for screenshot detection.
    
    This adapter loads a sequence classification model and uses it to determine
    whether a screenshot should be taken based on the conversation context.
    
    Optimizations:
    - torch.compile() for kernel fusion (PyTorch 2.0+)
    - Dynamic padding instead of fixed max_length
    - torch.inference_mode() for faster inference
    
    History handling:
    - Receives raw user texts from session handler
    - Trims history using its own tokenizer (centralized, DRY)
    - Formats as: "USER: {utt1}\\nUSER: {utt2}\\n..."
    """
    
    _instance: "ClassifierToolAdapter | None" = None
    
    def __init__(
        self,
        model_path: str,
        threshold: float = 0.66,
        history_max_tokens: int = 1200,
        device: str | None = None,
        compile_model: bool = True,
    ) -> None:
        """Initialize the classifier adapter.
        
        Args:
            model_path: HuggingFace model ID or local path
            threshold: Probability threshold for positive classification
            history_max_tokens: Max tokens for user-only history
            device: Device to run on ('cuda', 'cpu', or None for auto)
            compile_model: Whether to use torch.compile() for speedup
        """
        self.model_path = model_path
        self.threshold = threshold
        self.history_max_tokens = history_max_tokens
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(
            "Loading classifier model from %s (device=%s, threshold=%.2f)",
            model_path, self.device, threshold
        )
        
        # Load model and tokenizer
        self._tokenizer: PreTrainedTokenizerFast = AutoTokenizer.from_pretrained(model_path)
        self._tokenizer.truncation_side = "left"  # Keep most recent context
        self._newline_token_count = len(
            self._tokenizer.encode("\n", add_special_tokens=False)
        )
        self._count_tokens_cached = lru_cache(maxsize=4096)(self._count_tokens_uncached)
        
        self._model: PreTrainedModel = AutoModelForSequenceClassification.from_pretrained(model_path)
        self._model.to(self.device)
        self._model.eval()
        
        # Disable torch.compile to avoid CUDA graph pool conflicts when running in parallel
        if compile_model:
            logger.warning(
                "CLASSIFIER_COMPILE requested but disabled to avoid mempool conflicts under concurrency"
            )
        
        logger.info("Classifier model loaded successfully")
    
    @classmethod
    def get_instance(
        cls,
        model_path: str,
        threshold: float = 0.66,
        compile_model: bool = True,
    ) -> "ClassifierToolAdapter":
        """Get or create singleton instance of the classifier adapter."""
        if cls._instance is None:
            cls._instance = cls(
                model_path=model_path,
                threshold=threshold,
                compile_model=compile_model,
            )
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
    
    def _count_tokens_uncached(self, text: str) -> int:
        if not text:
            return 0
        return len(self._tokenizer.encode(text, add_special_tokens=False))

    def count_tokens(self, text: str) -> int:
        """Count tokens using the classifier's tokenizer (cached per unique text)."""
        return self._count_tokens_cached(text or "")
    
    def trim_user_history(self, user_texts: list[str]) -> str:
        """Trim user history to fit within token budget.
        
        Args:
            user_texts: List of raw user utterances (most recent last)
        
        Returns:
            Formatted history string: "USER: {utt1}\\nUSER: {utt2}\\n..."
            trimmed to fit within history_max_tokens.
        """
        if not user_texts:
            return ""
        
        newline_tokens = self._newline_token_count or 0
        selected: list[str] = []
        total_tokens = 0
        
        for text in reversed(user_texts):
            stripped = text.strip()
            if not stripped:
                continue
            line = f"USER: {stripped}"
            line_tokens = self.count_tokens(line)
            additional = line_tokens
            if selected:
                additional += newline_tokens
            if selected and total_tokens + additional > self.history_max_tokens:
                break
            selected.insert(0, line)
            total_tokens += additional
        
        return "\n".join(selected)
    
    def _format_input(self, user_utt: str, user_history: str = "") -> str:
        """Format input text for the classifier.
        
        The classifier expects input formatted as:
        USER: {utterance1}
        USER: {utterance2}
        ...
        USER: {current_utterance}
        
        Args:
            user_utt: Current user utterance (raw, without prefix)
            user_history: Pre-formatted user-only history (already has USER: prefixes)
        """
        lines: list[str] = []
        
        # Add history if present
        if user_history and user_history.strip():
            lines.append(user_history.strip())
        
        # Add current utterance with USER: prefix
        current = user_utt.strip()
        if not current.upper().startswith("USER:"):
            current = f"USER: {current}"
        lines.append(current)
        
        return "\n".join(lines)
    
    def classify(self, user_utt: str, user_history: str = "") -> tuple[bool, float]:
        """Classify whether a screenshot should be taken.
        
        Args:
            user_utt: The current user utterance
            user_history: Pre-formatted user-only history ("USER: {utt}" lines,
                          already trimmed to token budget by session handler)
        
        Returns:
            Tuple of (should_screenshot, probability)
        """
        # Format the full input
        text = self._format_input(user_utt, user_history)
        
        with torch.inference_mode():
            # Tokenize with dynamic padding
            # History is already trimmed to budget, but set max_length as safety cap
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=CLASSIFIER_MAX_LENGTH,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Run inference
            outputs = self._model(**inputs)
            probs = outputs.logits.softmax(dim=-1)[0]
            
            # Index 1 is "take_screenshot" class
            p_yes = probs[1].item()
            should_screenshot = p_yes >= self.threshold
            
            return should_screenshot, p_yes
    
    def run_tool_inference(self, user_utt: str, user_history: str = "") -> str:
        """Run tool inference and return JSON result.
        
        This method matches the interface expected by the tool runner.
        
        Args:
            user_utt: The current user utterance
            user_history: Pre-formatted user-only history (from session handler)
        
        Returns:
            JSON string: '[{"name": "take_screenshot"}]' or '[]'
        """
        should_screenshot, p_yes = self.classify(user_utt, user_history)
        
        logger.debug(
            "Classifier result: should_screenshot=%s p_yes=%.3f user_utt=%r",
            should_screenshot, p_yes, user_utt[:50]
        )
        
        if should_screenshot:
            return '[{"name": "take_screenshot"}]'
        return "[]"


__all__ = ["ClassifierToolAdapter"]
