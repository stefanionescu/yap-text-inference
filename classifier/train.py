from __future__ import annotations

"""Fine-tune a Longformer classifier for screenshot intent detection.

This script builds a dataset from `tests/messages/tool.py`, trains a
`allenai/longformer-base-4096` classifier (or another HF model you pass in),
and saves the model + tokenizer to a local directory.
"""

import argparse
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    set_seed,
)

from .data import ToolExample, build_examples, train_eval_split


def _truncate_conversation_text(text: str, tokenizer, max_length: int) -> str:
    """Truncate by dropping whole utterances (oldest first) to fit `max_length` tokens.

    We rely on newline-separated "USER: ..." lines. We keep *complete* lines from
    the end of the conversation, removing whole lines from the start until the
    encoded length (with special tokens) is <= max_length.
    """

    # Single-utterance case – let normal token truncation handle any overflow.
    lines = text.split("\n")
    if len(lines) <= 1:
        return text

    kept_from_end: list[str] = []
    # Walk utterances from newest to oldest, building up from the end.
    for line in reversed(lines):
        candidate_lines = [line] + kept_from_end
        candidate_text = "\n".join(candidate_lines)
        encoded = tokenizer(candidate_text, add_special_tokens=True)
        length = len(encoded.get("input_ids", []))
        if length <= max_length:
            # Safe to keep this older utterance as well.
            kept_from_end.insert(0, line)
        else:
            # Adding this line would exceed the limit; stop here.
            break

    if not kept_from_end:
        # Even the latest utterance alone is too long; fall back to it and let
        # normal token-level truncation handle the overflow.
        return lines[-1]

    return "\n".join(kept_from_end)


class ToolDataset(Dataset):
    """PyTorch dataset wrapping a list of `ToolExample` instances.

    This dataset performs tokenization inside `__getitem__` so that the Trainer
    receives fully encoded features (`input_ids`, `attention_mask`,
    `global_attention_mask`, `labels`) and we don't rely on custom collate
    functions or unused-column behavior.
    """

    def __init__(self, examples: list[ToolExample], tokenizer, max_length: int) -> None:
        self._examples = examples
        self._tokenizer = tokenizer
        self._max_length = max_length

    def __len__(self) -> int:  # type: ignore[override]
        return len(self._examples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:  # type: ignore[override]
        ex = self._examples[idx]
        # First truncate at the utterance level so we only ever drop *whole*
        # user turns from the start of the history.
        truncated_text = _truncate_conversation_text(ex.text, self._tokenizer, self._max_length)

        encodings = self._tokenizer(
            truncated_text,
            truncation=True,
            padding="max_length",
            max_length=self._max_length,
        )

        item: Dict[str, Any] = {
            key: torch.tensor(value) for key, value in encodings.items()
        }

        attention_mask = item.get("attention_mask")
        if attention_mask is not None:
            # attention_mask is shape [seq_len] for a single example
            global_attention_mask = torch.zeros_like(attention_mask)
            global_attention_mask[0] = 1  # first token gets global attention
            item["global_attention_mask"] = global_attention_mask

        item["labels"] = torch.tensor(int(ex.label), dtype=torch.long)
        return item


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train Longformer screenshot intent classifier")
    parser.add_argument(
        "--model-name",
        default="allenai/longformer-base-4096",
        help="Base HF model name to fine-tune (default: allenai/longformer-base-4096)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "models" / "longformer_screenshot_classifier"),
        help="Directory to save the fine-tuned model and tokenizer (default: classifier/models/longformer_screenshot_classifier)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs (default: 3)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Per-device batch size (default: 16)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="Learning rate (default: 2e-5)",
    )
    parser.add_argument(
        "--eval-fraction",
        type=float,
        default=0.2,
        help="Fraction of groups to reserve for evaluation (default: 0.2)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=1536,
        help="Maximum sequence length in tokens (default: 1536)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for splitting and training (default: 42)",
    )
    return parser


def _compute_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> Dict[str, float]:
    logits, labels = eval_pred
    preds = logits.argmax(axis=-1)

    acc = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary", zero_division=0
    )

    return {
        "accuracy": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    set_seed(args.seed)

    # Build dataset from regression messages
    all_examples = build_examples()
    train_examples, eval_examples = train_eval_split(
        all_examples,
        eval_fraction=args.eval_fraction,
        seed=args.seed,
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    # Keep the most recent `max_length` tokens when truncating long histories
    tokenizer.truncation_side = "left"

    train_dataset = ToolDataset(train_examples, tokenizer, args.max_length)
    eval_dataset = ToolDataset(eval_examples, tokenizer, args.max_length)

    id2label = {0: "no_screenshot", 1: "take_screenshot"}
    label2id = {v: k for k, v in id2label.items()}

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=2,
        id2label=id2label,
        label2id=label2id,
    )

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Note: we keep TrainingArguments usage minimal to stay compatible with a
    # wide range of transformers versions. Evaluation is run explicitly at the
    # end via `trainer.evaluate()`.
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=float(args.epochs),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        save_strategy="no",  # Don't save intermediate checkpoints
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        compute_metrics=_compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print("Evaluation metrics:", metrics)

    # Save final model + tokenizer
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))


if __name__ == "__main__":
    main()
