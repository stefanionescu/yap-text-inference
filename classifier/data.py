from __future__ import annotations

"""Dataset construction utilities for the screenshot intent classifier.

This module turns the curated regression tests in
`tests/messages/tool.py` into a list of training examples
(history + latest user message, plus a binary label).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import random
import sys

# Ensure the repository root is on sys.path so we can import tests.messages.tool
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.messages.tool import TOOL_DEFAULT_MESSAGES  # type: ignore[import]


@dataclass
class ToolExample:
    """Single training example.

    Attributes:
        text: The normalized text input (conversation history + latest user message).
        label: Integer label (0 = no screenshot, 1 = take screenshot).
        group: Group identifier used to keep related examples together when
            creating train/eval splits (e.g. all turns from one conversation).
    """

    text: str
    label: int
    group: str


def _format_single_turn(text: str) -> str:
    """Format a single user utterance as a training text.

    We prefix with "USER:" so the classifier can later be used with
    similar formatting at inference time.
    """

    return f"USER: {text}"


def build_examples() -> list[ToolExample]:
    """Build examples from `TOOL_DEFAULT_MESSAGES`.

    For single-turn entries of the form `(text, bool)`, we create a single
    example with just that user message.

    For multi-turn entries of the form `(name, [(text, bool), ...])`, we create
    one example per turn, where the `text` field is the concatenation of all
    user messages up to and including that turn, separated by newlines.
    """

    examples: list[ToolExample] = []

    for idx, item in enumerate(TOOL_DEFAULT_MESSAGES):
        # Simple case: (text, bool)
        if (
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], bool)
        ):
            text, label = item
            group = f"single_{idx}"
            examples.append(
                ToolExample(
                    text=_format_single_turn(text),
                    label=int(label),
                    group=group,
                )
            )
            continue

        # Conversation case: (name, [(text, bool), ...])
        if (
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], list)
        ):
            conv_name, turns = item
            history_lines: list[str] = []
            group = f"conv_{conv_name}"

            for turn_index, turn in enumerate(turns):
                if (
                    not isinstance(turn, tuple)
                    or len(turn) != 2
                    or not isinstance(turn[0], str)
                    or not isinstance(turn[1], bool)
                ):
                    raise TypeError(
                        f"Unexpected turn structure in conversation '{conv_name}' "
                        f"at index {turn_index}: {turn!r}"
                    )

                utterance, label = turn
                history_lines.append(f"USER: {utterance}")
                context_text = "\n".join(history_lines)

                examples.append(
                    ToolExample(
                        text=context_text,
                        label=int(label),
                        group=group,
                    )
                )
            continue

        raise TypeError(f"Unexpected TOOL_DEFAULT_MESSAGES entry at index {idx}: {item!r}")

    return examples


def train_eval_split(
    examples: Sequence[ToolExample],
    eval_fraction: float = 0.2,
    seed: int = 42,
) -> tuple[list[ToolExample], list[ToolExample]]:
    """Split examples into train/eval sets while keeping groups together.

    Args:
        examples: All available examples.
        eval_fraction: Fraction of *groups* to assign to the eval set.
        seed: Random seed for reproducibility.

    Returns:
        (train_examples, eval_examples)
    """

    if not 0.0 < eval_fraction < 1.0:
        raise ValueError("eval_fraction must be between 0 and 1 (exclusive)")

    # Group examples by conversation/group id
    grouped: dict[str, list[ToolExample]] = {}
    for ex in examples:
        grouped.setdefault(ex.group, []).append(ex)

    group_names = list(grouped.keys())
    rng = random.Random(seed)
    rng.shuffle(group_names)

    n_eval_groups = max(1, int(len(group_names) * eval_fraction))
    eval_group_names = set(group_names[:n_eval_groups])

    train_examples: list[ToolExample] = []
    eval_examples: list[ToolExample] = []

    for group_name, group_examples in grouped.items():
        target = eval_examples if group_name in eval_group_names else train_examples
        target.extend(group_examples)

    return train_examples, eval_examples


def iter_text_label(examples: Iterable[ToolExample]) -> Iterable[tuple[str, int]]:
    """Convenience generator yielding (text, label) pairs."""

    for ex in examples:
        yield ex.text, ex.label
