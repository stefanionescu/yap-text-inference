from __future__ import annotations

"""Evaluate the trained classifier on simple local test cases.

This script loads the Longformer screenshot intent classifier from a local
model directory and runs it against the small set of conversations defined in
`classifier/test_cases.py`.

It prints overall accuracy and a list of misclassified turns, similar in
spirit to the reporting you get from `tests/tool.py` for the live tool-call
suite, but fully offline and classifier-only.
"""

import argparse
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import sys

# Ensure the project root (which contains the `classifier` package) is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from classifier.test_cases import TESTS


def _truncate_conversation_text(text: str, tokenizer: AutoTokenizer, max_length: int) -> str:
    """Truncate by dropping whole utterances (oldest first) to fit `max_length` tokens.

    We assume the text is newline-separated "USER: ..." lines, just like in
    training. We keep complete lines from the end, removing whole lines from
    the start until the encoded length (with special tokens) is <= max_length.
    """

    lines = text.split("\n")
    if len(lines) <= 1:
        return text

    kept_from_end: list[str] = []
    for line in reversed(lines):
        candidate_lines = [line] + kept_from_end
        candidate_text = "\n".join(candidate_lines)
        encoded = tokenizer(candidate_text, add_special_tokens=True)
        length = len(encoded.get("input_ids", []))
        if length <= max_length:
            kept_from_end.insert(0, line)
        else:
            break

    if not kept_from_end:
        # Even the latest utterance alone is too long; fall back to it and let
        # token-level truncation handle overflow.
        return lines[-1]

    return "\n".join(kept_from_end)


@dataclass
class EvalExample:
    convo_name: str
    turn_index: int
    text: str
    expected: int
    prob_yes: float
    predicted: int
    ttfb_ms: float | None = None  # Time to first logit (forward pass start to logit output)
    total_ms: float | None = None  # Total time (tokenization + forward pass + softmax)


def _iter_conversation_examples() -> Iterable[Tuple[str, int, str, int]]:
    """Yield (convo_name, turn_index, text, expected_label) examples.

    Handles both:
    - Single-turn entries: (text, bool) -> one example
    - Multi-turn entries: (conversation_name, [(text, bool), ...]) -> one example per turn

    For each turn, we build cumulative user-only history, like in training.
    """

    for idx, item in enumerate(TESTS):
        if not isinstance(item, tuple) or len(item) != 2:
            continue

        first, second = item

        # Single-turn case: (text, bool)
        if isinstance(first, str) and isinstance(second, bool):
            convo_name = f"single_{idx}"
            text = f"USER: {first}"
            yield convo_name, 0, text, int(second)
            continue

        # Multi-turn case: (conversation_name, [(text, bool), ...])
        if isinstance(first, str) and isinstance(second, list):
            convo_name = first
            turns = second
            history_lines: List[str] = []
            for turn_index, turn in enumerate(turns):
                if not (isinstance(turn, tuple) and len(turn) == 2):
                    continue
                utt, label = turn
                if not (isinstance(utt, str) and isinstance(label, bool)):
                    continue
                history_lines.append(f"USER: {utt}")
                text = "\n".join(history_lines)
                yield convo_name, turn_index, text, int(label)
            continue


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate screenshot classifier on local test cases")
    parser.add_argument(
        "--model-dir",
        type=str,
        default=str(
            Path(__file__).resolve().parent / "models" / "longformer_screenshot_classifier"
        ),
        help="Path to the trained model directory (default: classifier/models/longformer_screenshot_classifier)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=3000,
        help="Maximum sequence length for tokenization (default: 3000)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision threshold for the positive class (default: 0.5)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent classifier evaluations (default: 1)",
    )
    return parser


def _percentile(sorted_values: list[float], percentile: float) -> float:
    """Calculate percentile from sorted list of values."""
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def _print_latency_summary(examples: List[EvalExample]) -> None:
    """Print latency statistics (p50, p90, p95) for TTFB and total time."""
    ttfb_samples: list[float] = []
    total_samples: list[float] = []
    for ex in examples:
        if ex.ttfb_ms is not None:
            ttfb_samples.append(ex.ttfb_ms)
        if ex.total_ms is not None:
            total_samples.append(ex.total_ms)

    if not ttfb_samples and not total_samples:
        return

    print("\nLatency (classifier inference, ms):")
    if ttfb_samples:
        values = sorted(ttfb_samples)
        p50 = _percentile(values, 50)
        p90 = _percentile(values, 90)
        p95 = _percentile(values, 95)
        print(f"  TTFB: p50={p50:.1f} ms  p90={p90:.1f} ms  p95={p95:.1f} ms  (n={len(values)})")
    if total_samples:
        values = sorted(total_samples)
        p50 = _percentile(values, 50)
        p90 = _percentile(values, 90)
        p95 = _percentile(values, 95)
        print(f"  Total: p50={p50:.1f} ms  p90={p90:.1f} ms  p95={p95:.1f} ms  (n={len(values)})")


def _run_single_inference(
    tokenizer: AutoTokenizer,
    model: torch.nn.Module,
    device: torch.device,
    max_length: int,
    threshold: float,
    convo_name: str,
    turn_index: int,
    text: str,
    expected: int,
) -> EvalExample:
    """Run a single classifier inference and return the result with timing."""
    with torch.no_grad():
        # Utterance-level truncation: drop whole turns from the start until the
        # encoded sequence fits within `max_length` tokens.
        t0_tokenize = time.perf_counter()
        truncated_text = _truncate_conversation_text(text, tokenizer, max_length)
        inputs = tokenizer(
            truncated_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        t1_tokenize = time.perf_counter()

        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            global_attention_mask = torch.zeros_like(attention_mask)
            global_attention_mask[:, 0] = 1
        else:
            global_attention_mask = None

        # Forward pass timing (TTFB = time until we get logits)
        t0_forward = time.perf_counter()
        outputs = model(
            **inputs,
            global_attention_mask=global_attention_mask,
        )
        t1_forward = time.perf_counter()

        # Softmax timing
        t0_softmax = time.perf_counter()
        probs = outputs.logits.softmax(dim=-1)[0]
        p_no, p_yes = probs.tolist()
        predicted = int(p_yes >= threshold)
        t1_softmax = time.perf_counter()

        # Calculate timings
        ttfb_ms = (t1_forward - t0_forward) * 1000.0  # Forward pass time
        total_ms = (t1_softmax - t0_tokenize) * 1000.0  # Total time (tokenize + forward + softmax)

        return EvalExample(
            convo_name=convo_name,
            turn_index=turn_index,
            text=truncated_text,
            expected=expected,
            prob_yes=p_yes,
            predicted=predicted,
            ttfb_ms=ttfb_ms,
            total_ms=total_ms,
        )


def _run_eval(model_dir: Path, max_length: int, threshold: float, concurrency: int) -> None:
    if not model_dir.exists():
        raise SystemExit(f"Model directory does not exist: {model_dir}")

    print(f"[classifier] Loading model from {model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    # Keep the most recent `max_length` tokens when truncating long histories
    tokenizer.truncation_side = "left"
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Collect all examples first to know total count for progress bar
    all_examples_list = list(_iter_conversation_examples())
    total_examples = len(all_examples_list)

    examples: List[EvalExample] = []
    bar_width = 30
    progress_lock = threading.Lock()
    completed_count = 0

    effective_concurrency = max(1, concurrency)
    print(f"Running {total_examples} classifier evaluations (concurrency={effective_concurrency})...")

    def _render_progress(completed: int, total: int) -> None:
        total = max(1, total)
        ratio = min(max(completed / total, 0.0), 1.0)
        filled = int(bar_width * ratio)
        bar = "#" * filled + "-" * (bar_width - filled)
        line = f"\rProgress [{bar}] {completed}/{total} ({ratio * 100:5.1f}%)"
        end = "\n" if completed >= total else ""
        print(line, end=end, flush=True)

    def _process_example(idx: int, item: Tuple[str, int, str, int]) -> Tuple[int, EvalExample]:
        convo_name, turn_index, text, expected = item
        result = _run_single_inference(
            tokenizer=tokenizer,
            model=model,
            device=device,
            max_length=max_length,
            threshold=threshold,
            convo_name=convo_name,
            turn_index=turn_index,
            text=text,
            expected=expected,
        )
        return idx, result

    # Use ThreadPoolExecutor for concurrent inference
    with ThreadPoolExecutor(max_workers=effective_concurrency) as executor:
        # Submit all tasks
        future_to_idx = {
            executor.submit(_process_example, idx, item): idx
            for idx, item in enumerate(all_examples_list)
        }

        # Collect results as they complete, maintaining order
        results: List[EvalExample | None] = [None] * total_examples

        for future in as_completed(future_to_idx):
            idx, result = future.result()
            results[idx] = result

            # Thread-safe progress update
            with progress_lock:
                completed_count += 1
                _render_progress(completed_count, total_examples)

    # Flatten results (they're already in order)
    examples = [r for r in results if r is not None]

    total = len(examples)
    correct = sum(1 for ex in examples if ex.predicted == ex.expected)
    accuracy = correct / total if total else 0.0

    print(f"\n[classifier] Evaluated {total} turns across {len(TESTS)} conversations")
    print(f"[classifier] Accuracy: {accuracy:.3f} ({correct}/{total}) with threshold={threshold:.2f}")

    # Print latency summary
    _print_latency_summary(examples)

    # Print misclassified examples
    failures = [ex for ex in examples if ex.predicted != ex.expected]
    if not failures:
        print("\n[classifier] All test turns classified correctly.")
        return

    print("\n[classifier] Misclassified turns:")
    for ex in failures:
        print("- conversation=", ex.convo_name, "turn=", ex.turn_index)
        print("  expected=", ex.expected, "predicted=", ex.predicted, f"p_yes={ex.prob_yes:.3f}")
        # Show only the latest line for brevity
        last_line = ex.text.splitlines()[-1] if ex.text else ""
        print("  last_utt=", last_line)


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    model_dir = Path(args.model_dir).expanduser().resolve()
    _run_eval(
        model_dir=model_dir,
        max_length=args.max_length,
        threshold=args.threshold,
        concurrency=args.concurrency,
    )


if __name__ == "__main__":
    main()
