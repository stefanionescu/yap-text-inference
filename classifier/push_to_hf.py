from __future__ import annotations

"""Push a trained screenshot intent classifier to Hugging Face Hub.

By default this script pushes the ModernBERT checkpoint from
`classifier/models/modernbert_screenshot_classifier/` to
`yapwithai/yap-modernbert-screenshot-intent`. Pass `--variant longformer` (or
explicit `--model-dir` / `--repo-id` values) to push the Longformer weights
instead.

In both cases the script can also create/overwrite a simple model card
(`README.md`) in the model directory before uploading.

Authentication uses either the `--hf-token` flag or the `HF_TOKEN` /
`HUGGINGFACE_TOKEN` environment variables.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer


MODELS_DIR = Path(__file__).resolve().parent / "models"
VARIANTS = {
    "modernbert": {
        "readable_name": "ModernBERT",
        "model_dir": MODELS_DIR / "modernbert_screenshot_classifier",
        "repo_id": "yapwithai/yap-modernbert-screenshot-intent",
        "base_model": "answerdotai/ModernBERT-base",
        "tag": "modernbert",
    },
    "longformer": {
        "readable_name": "Longformer",
        "model_dir": MODELS_DIR / "longformer_screenshot_classifier",
        "repo_id": "yapwithai/yap-longformer-screenshot-intent",
        "base_model": "allenai/longformer-base-4096",
        "tag": "longformer",
    },
}
DEFAULT_VARIANT = "modernbert"


def _build_readme(repo_id: str, base_model: str, variant_key: str) -> str:
    """Return a default README/model card for the Hub repo."""
    variant = VARIANTS[variant_key]
    readable_name = variant["readable_name"]
    tag = variant["tag"]

    if variant_key == "longformer":
        base_description = (
            '"longformer-base-4096" is a RoBERTa-style encoder with support for sequences up '
            "to 4,096 tokens using a combination of sliding-window local attention and "
            "user-configured global attention. We follow the common pattern for classification "
            "tasks with Longformer by assigning global attention to the first token in each sequence."
        )
        usage_block = f"""```python
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
    max_length=1536,
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
```"""
        citation_heading = "Longformer Citation"
        citation_block = """```bibtex
@article{Beltagy2020Longformer,
  title={Longformer: The Long-Document Transformer},
  author={Iz Beltagy and Matthew E. Peters and Arman Cohan},
  journal={arXiv:2004.05150},
  year={2020},
}
```

Longformer is an open-source project developed by the Allen Institute for Artificial Intelligence (AI2).
"""
    else:
        base_description = (
            "ModernBERT-base pairs a fast, memory-efficient encoder with strong long-context fine-tuning "
            "and inference characteristics. It supports long inputs without requiring manual global "
            "attention masks, making it a drop-in replacement for standard encoder classifiers."
        )
        usage_block = f"""```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

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
    max_length=1536,
)

with torch.no_grad():
    outputs = model(**inputs)
    probs = outputs.logits.softmax(dim=-1)[0]

p_no, p_yes = probs.tolist()
print("P(no_screenshot)=", p_no)
print("P(take_screenshot)=", p_yes)
```"""
        citation_heading = "ModernBERT Citation"
        citation_block = """```bibtex
@misc{modernbert,
      title={Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference},
      author={Benjamin Warner and Antoine Chaffin and Benjamin Clavié and Orion Weller and Oskar Hallström and Said Taghadouini and Alexis Gallagher and Raja Biswas and Faisal Ladhak and Tom Aarsen and Nathan Cooper and Griffin Adams and Jeremy Howard and Iacopo Poli},
      year={2024},
      eprint={2412.13663},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2412.13663},
}
```

ModernBERT is developed by Answer.AI and collaborators.
"""

    return f"""---
language: en
license: apache-2.0
base_model: {base_model}
pipeline_tag: text-classification
tags:
  - {tag}
  - intent-classification
  - tool-calling
  - screenshots
---

# Screenshot Intent Classifier

This repository contains a {readable_name}-based classifier fine-tuned to decide
**whether a conversational agent should trigger a screenshot tool** for the
latest user message.

## Base Model

This model is fine-tuned from [`{base_model}`](https://huggingface.co/{base_model}),
and inherits the base encoder's maximum context length and tokenizer.
{base_description}

## Classifier

- `0` / `no_screenshot`: do not call the screenshot tool.
- `1` / `take_screenshot`: call the screenshot tool.

The input is a text block representing the recent conversation history,
formatted as one utterance per line, prefixed with a speaker tag, e.g.:

```text
USER: I'm wondering if blue goes well with yellow.
USER: What's your take on this?
```

At inference time, the host application typically feeds the last few
conversation turns (most importantly the latest user message) in this format
and thresholds the classifier's `take_screenshot` probability to decide
whether to trigger the tool.

## Training Data

The classifier was trained on a curated, hand-labelled private dataset. It
contains hundreds of single-turn and multi-turn examples specifying whether
each user message **should** or **should not** trigger a screenshot, including:

- Clear positive triggers ("look at this", "check this out", "rate this pic").
- Clear negatives (off-topic chit-chat, abstract statements, idioms like
  "I'll look into it").
- Edge cases involving deictic pronouns, quantities ("take 2 screenshots"),
  negation ("don't look"), multi-turn context, and more.

No external user logs or third-party datasets were used; the training data is
purely synthetic / curated for this intent task.

## Training Setup

Approximate defaults:

- Epochs: 3
- Batch size: 16 (per device)
- Learning rate: 2e-5
- Weight decay: 0.01
- Max sequence length: 1536 tokens (truncation for old entries applied beyond this)

The script builds examples by concatenating conversation history up to and
including the current user message, one utterance per line prefixed with
`"USER:"`. Multi-turn conversations therefore become multiple training examples
with growing context.

## Usage

Basic usage with the Transformers library:

{usage_block}

In production, you would:

- Construct a conversation history string similar to the training format
  (recent user turns, optionally assistant turns, each on its own line with a
  speaker prefix).
- Run the classifier once per latest user message.
- Threshold `p_yes` to decide whether to trigger the screenshot tool.

## {citation_heading}

If you use {readable_name} in your work, please cite:

{citation_block}
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


def _ensure_readme(
    model_dir: Path,
    *,
    repo_id: str,
    base_model: str,
    variant_key: str,
    overwrite: bool,
) -> None:
    readme_path = model_dir / "README.md"
    if readme_path.exists() and not overwrite:
        return
    content = _build_readme(
        repo_id=repo_id,
        base_model=base_model,
        variant_key=variant_key,
    )
    readme_path.write_text(content, encoding="utf-8")


def _sanitize_base_model(candidate: Optional[str], default: str) -> str:
    """Return a valid base model id for the README front matter."""
    if not candidate:
        return default

    candidate = candidate.strip()
    # Absolute/local paths are invalid as HF model ids.
    if Path(candidate).is_absolute():
        return default
    return candidate or default


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push trained classifier to Hugging Face Hub")
    parser.add_argument(
        "--variant",
        choices=sorted(VARIANTS.keys()),
        default=DEFAULT_VARIANT,
        help=(
            "Built-in classifier variant to push (default: modernbert). "
            "Controls default model dir + repo id."
        ),
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        help="Path to the trained model directory to push (defaults to the variant's dir).",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        help="Target Hugging Face repo id (defaults to the variant's recommended repo).",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        help="Optional base model name to mention in the generated README.",
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

    variant = VARIANTS[args.variant]

    model_dir = Path(args.model_dir or variant["model_dir"]).expanduser().resolve()
    if not model_dir.exists():
        raise SystemExit(f"Model directory does not exist: {model_dir}")

    repo_id = args.repo_id or variant["repo_id"]

    token = _resolve_token(args.hf_token)

    config = AutoConfig.from_pretrained(str(model_dir))
    raw_base_model = (
        args.base_model
        or getattr(config, "_name_or_path", None)
        or getattr(config, "name_or_path", None)
        or getattr(config, "base_model_name_or_path", None)
        or variant["base_model"]
    )
    inferred_base_model = _sanitize_base_model(raw_base_model, variant["base_model"])
    if inferred_base_model != raw_base_model:
        print(
            "[classifier] NOTE: base_model metadata was not a Hugging Face repo id; "
            f"using '{inferred_base_model}' in README."
        )

    # Optionally create/overwrite README in the model directory
    _ensure_readme(
        model_dir,
        repo_id=repo_id,
        base_model=inferred_base_model,
        variant_key=args.variant,
        overwrite=args.overwrite_readme,
    )

    print("[classifier] Loading model from", model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))

    print("[classifier] Pushing model to Hugging Face Hub repo:", repo_id)
    # `use_auth_token` is still widely supported; if using a very new transformers
    # version, it will be passed through to huggingface_hub.
    model.push_to_hub(repo_id, use_auth_token=token)
    tokenizer.push_to_hub(repo_id, use_auth_token=token)

    # Upload README.md explicitly (push_to_hub doesn't include it)
    readme_path = model_dir / "README.md"
    if readme_path.exists():
        print("[classifier] Uploading README.md...")
        api = HfApi()
        api.upload_file(
            path_or_fileobj=str(readme_path),
            path_in_repo="README.md",
            repo_id=repo_id,
            token=token,
        )

    print("[classifier] Push complete.")


if __name__ == "__main__":
    main()
