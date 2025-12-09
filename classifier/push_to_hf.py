from __future__ import annotations

"""Push a trained screenshot intent classifier to Hugging Face Hub.

By default this script:
- Loads the model + tokenizer from `classifier/models/longformer_screenshot_classifier/`.
- Pushes to the `yapwithai/yap-function-caller` repository.
- Creates a simple model card `README.md` in the model directory if one
  doesn't already exist.

You can override the model directory and target repo via CLI flags.
Authentication uses either the `--hf-token` flag or the `HF_TOKEN` /\
`HUGGINGFACE_TOKEN` environment variables.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from transformers import AutoModelForSequenceClassification, AutoTokenizer


DEFAULT_REPO_ID = "yapwithai/yap-function-caller"
DEFAULT_MODEL_DIR = (
    Path(__file__).resolve().parent / "models" / "longformer_screenshot_classifier"
)
BASE_MODEL = "allenai/longformer-base-4096"


def _build_readme(repo_id: str, base_model: str) -> str:
    """Return a default README/model card for the Hub repo.

    This card is intentionally concise and focuses on:
    - What the model does (screenshot intent detection)
    - Where it comes from (base model)
    - How it was trained at a high level
    """

    return f"""---
language: en
license: apache-2.0
base_model: {base_model}
pipeline_tag: text-classification
tags:
  - longformer
  - intent-classification
  - tool-calling
  - screenshots
  - yapwithai
---

# Screenshot intent classifier (Longformer)

This repository contains a Longformer-based classifier fine-tuned to decide
**whether a conversational agent should trigger a screenshot tool** for the
latest user message, given conversational context.

The classifier is designed for use in the `yap-text-inference` stack
(`yapwithai`) and powers screenshot intent decisions such as whether to call a
`take_screenshot` tool.

## Base model

This model is fine-tuned from [`{base_model}`](https://huggingface.co/{base_model}),
"longformer-base-4096", a RoBERTa-style encoder with support for sequences up
to 4,096 tokens using a combination of sliding-window local attention and
user-configured global attention.

We follow the common pattern for classification tasks with Longformer by
assigning **global attention to the first token** in each sequence.

## Task

**Binary classification**:

- `0` / `no_screenshot`: do not call the screenshot tool.
- `1` / `take_screenshot`: call the screenshot tool.

The input is a short text block representing the recent conversation history,
formatted as one utterance per line, prefixed with a speaker tag, e.g.:

```text
USER: I'm wondering if blue goes well with yellow.
USER: What's your take on this?
```

At inference time, the host application typically feeds the last few
conversation turns (most importantly the latest user message) in this format
and thresholds the classifier's `take_screenshot` probability to decide
whether to trigger the tool.

## Training data

The classifier was trained on a curated, hand-labelled dataset derived from
`tests/messages/tool.py` in the `yap-text-inference` repository. That file
contains hundreds of single-turn and multi-turn examples specifying whether
each user message **should** or **should not** trigger a screenshot, including:

- Clear positive triggers ("look at this", "check this out", "rate this pic").
- Clear negatives (capability questions, off-topic chit-chat, abstract
  statements, idioms like "I'll look into it").
- Edge cases involving deictic pronouns, quantities ("take 2 screenshots"),
  negation ("don't look"), multi-turn context, and more.

No external user logs or third-party datasets were used; the training data is
purely synthetic / curated for this intent task.

## Training setup (reference)

The reference training script lives at `classifier/train.py` in the
`yap-text-inference` repo and fine-tunes `{base_model}` using Hugging Face
`Trainer`. Approximate defaults:

- Epochs: 3
- Batch size: 16 (per device)
- Learning rate: 2e-5
- Weight decay: 0.01
- Max sequence length: 3000 tokens (truncation applied beyond this)

The script builds examples by concatenating conversation history up to and
including the current user message, one utterance per line prefixed with
`"USER:"`. Multi-turn test cases therefore become multiple training examples
with growing context.

## Usage

Basic usage with the Transformers library:

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

MODEL_ID = "{repo_id}"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
model.eval()

text = "USER: look at this amazing sunset"
inputs = tokenizer(
    text,
    return_tensors="pt",
    truncation=True,
    padding="max_length",
    max_length=3000,
)

attention_mask = inputs["attention_mask"]
global_attention_mask = torch.zeros_like(attention_mask)
global_attention_mask[:, 0] = 1

with torch.no_grad():
    outputs = model(**inputs, global_attention_mask=global_attention_mask)
    probs = outputs.logits.softmax(dim=-1)[0]

p_no, p_yes = probs.tolist()
print("P(no_screenshot)=", p_no)
print("P(take_screenshot)=", p_yes)
```

In production, you would:

- Construct a conversation history string similar to the training format
  (recent user turns, optionally assistant turns, each on its own line with a
  speaker prefix).
- Run the classifier once per latest user message.
- Threshold `p_yes` to decide whether to trigger the screenshot tool.

## Longformer citation

If you use this model in academic work, please also cite Longformer:

```bibtex
@article{Beltagy2020Longformer,
  title={Longformer: The Long-Document Transformer},
  author={Iz Beltagy and Matthew E. Peters and Arman Cohan},
  journal={arXiv:2004.05150},
  year={2020},
}
```

Longformer is an open-source project developed by the Allen Institute for
Artificial Intelligence (AI2).
"""


def _resolve_token(cli_token: Optional[str]) -> str:
    if cli_token:
        return cli_token
    env_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if env_token:
        return env_token
    msg = (
        "No Hugging Face token provided. Set HF_TOKEN / HUGGINGFACE_TOKEN or "
        "pass --hf-token."
    )
    raise SystemExit(msg)


def _ensure_readme(model_dir: Path, repo_id: str, base_model: str, overwrite: bool) -> None:
    readme_path = model_dir / "README.md"
    if readme_path.exists() and not overwrite:
        return
    content = _build_readme(repo_id=repo_id, base_model=base_model)
    readme_path.write_text(content, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push trained classifier to Hugging Face Hub")
    parser.add_argument(
        "--model-dir",
        type=str,
        default=str(DEFAULT_MODEL_DIR),
        help=(
            "Path to the trained model directory to push "
            f"(default: {DEFAULT_MODEL_DIR})"
        ),
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default=DEFAULT_REPO_ID,
        help=(
            "Target Hugging Face repo id, e.g. 'org/name' "
            f"(default: {DEFAULT_REPO_ID})"
        ),
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        help=(
            "Hugging Face access token. If omitted, HF_TOKEN or "
            "HUGGINGFACE_TOKEN env vars are used."
        ),
    )
    parser.add_argument(
        "--overwrite-readme",
        action="store_true",
        help="Overwrite an existing README.md in the model directory if present.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    model_dir = Path(args.model_dir).expanduser().resolve()
    if not model_dir.exists():
        raise SystemExit(f"Model directory does not exist: {model_dir}")

    token = _resolve_token(args.hf_token)

    # Optionally create/overwrite README in the model directory
    _ensure_readme(model_dir, repo_id=args.repo_id, base_model=BASE_MODEL, overwrite=args.overwrite_readme)

    print("[classifier] Loading model from", model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))

    print("[classifier] Pushing model to Hugging Face Hub repo:", args.repo_id)
    # `use_auth_token` is still widely supported; if using a very new transformers
    # version, it will be passed through to huggingface_hub.
    model.push_to_hub(args.repo_id, use_auth_token=token)
    tokenizer.push_to_hub(args.repo_id, use_auth_token=token)

    print("[classifier] Push complete.")


if __name__ == "__main__":
    main()
