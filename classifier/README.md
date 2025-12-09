### Screenshot intent classifier

This directory contains an **offline training pipeline** for a
`screenshot intent` classifier based on **Longformer**. The classifier is
trained on the curated regression prompts in `tests/messages/tool.py` and
predicts whether the system should call the `take_screenshot` tool for the
latest user message, given conversation context.

The goal is to provide a **fast, cheap, and stable** alternative to using a
full chat LLM for this yes/no decision, while supporting **longer contexts**
via `allenai/longformer-base-4096`.

---

### Contents

- **`__init__.py`**: Marks this directory as a Python package.
- **`requirements.txt`**: Minimal dependencies for training (Torch, Transformers,
  Accelerate, scikit-learn).
- **`data.py`**: Turns `TOOL_DEFAULT_MESSAGES` from `tests/messages/tool.py` into
  history-aware training examples and creates train/eval splits.
- **`train.py`**: Fine-tunes `allenai/longformer-base-4096` (by default) as a
  binary classifier and saves model + tokenizer locally.
- **`install.sh`**: Creates a dedicated virtualenv and installs deps.
- **`train.sh`**: Convenience wrapper to run training inside that virtualenv.
 - **`eval.py`**: Offline evaluation of the trained classifier on local test cases.
 - **`push_to_hf.py`**: Pushes a trained classifier to Hugging Face Hub.
 - **`push.sh`**: Convenience wrapper around `push_to_hf.py`.

---

### Prerequisites

- **Python**: 3.9+ recommended.
- **OS**: macOS / Linux. (Scripts are POSIX shell.)
- **Network access**: first run will download `allenai/longformer-base-4096`
  from Hugging Face.
- **Torch wheels**: depending on your platform (e.g. Apple Silicon), you may need
  a recent `pip` and/or extra steps if PyPI does not have a matching wheel.

All training happens offline against the existing test data in
`tests/messages/tool.py`. No external datasets are required.

---

### One-time setup

From the **repository root**:

```bash
bash classifier/install.sh
```

This will:

- Create a virtualenv at `.venv_classifier` (next to the repo).
- Install the packages listed in `classifier/requirements.txt` into that env.

If you want to choose a different Python binary (e.g. `python3.11`), set
`PYTHON_BIN` when running the installer:

```bash
PYTHON_BIN=python3.11 bash classifier/install.sh
```

---

### Training the classifier

From the **repository root**:

```bash
bash classifier/train.sh
```

This will:

- Activate `.venv_classifier`.
- Run `python -m classifier.train` with default hyperparameters.
- Fine-tune `allenai/longformer-base-4096` on the dataset derived from
  `tests/messages/tool.py`.
- Save the resulting model + tokenizer to
  `classifier/models/longformer_screenshot_classifier/` (by default).

You can customize training via CLI flags, e.g.:

```bash
bash classifier/train.sh \
  --epochs 5 \
  --batch-size 32 \
  --learning-rate 3e-5 \
  --max-length 1200 \
  --output-dir classifier/models/longformer_screenshot_classifier_v2
```

Run `./classifier/train.sh --help` for the full list of options.

---

### How the data is built

`classifier/data.py` imports `TOOL_DEFAULT_MESSAGES` from
`tests/messages/tool.py` and converts it into supervised examples:

- **Single-turn entries** like `("look at this", True)` become one example:
  - Text: `"USER: look at this"`
  - Label: `1` (take screenshot)
- **Multi-turn conversations** like `("context_switch", [(text, bool), ...])`:
  - For each turn, we create an example whose text is **all user messages up to
    that turn**, joined by newlines, e.g.:

    ```text
    USER: I'm wondering if blue goes well with yellow.
    USER: What's your take on this?
    ```

  - The label for that example is the boolean for the current turn.

We also assign a **group id** to each example (single or conversation). When
we split into train/eval, we reserve whole groups, so all turns from a given
conversation end up in the same split. This avoids leaking context between
train and eval.

---

### Model & training details

- **Base model**: `allenai/longformer-base-4096` (long-context encoder).
- **Head**: 2-way classification head (`no_screenshot`, `take_screenshot`).
- **Input format**:
  - Each training example is a text block consisting of user messages,
    one per line, prefixed with `"USER:"`.
  - At inference time you should feed text in the **same style** (e.g. last N
    user messages, prefixed and joined by newlines).
- **Tokenization**:
  - On-the-fly tokenization in the collate function (no pre-saved tokenized
    dataset).
  - Default `max_length=1200`; you can increase or decrease this as long as it
    stays within the model's maximum of 4096 tokens.
  - The collate function also constructs a `global_attention_mask` that assigns
    **global attention to the first token**, as recommended for Longformer
    classification tasks.
- **Training hyperparameters** (defaults):
  - Epochs: 3
  - Batch size: 16 (per device)
  - Learning rate: 2e-5
  - Weight decay: 0.01
  - Metric: F1 (binary, `take_screenshot` as the positive class)

`train.py` prints evaluation metrics at the end of training.

---

### Evaluating on local test cases

To quickly sanity-check the trained classifier on a small set of hand-picked
multi-turn conversations (defined in `classifier/test_cases.py`), you can use
the offline eval script.

From the **repository root**:

```bash
python classifier/eval.py
```

This will:

- Load the model from `classifier/models/longformer_screenshot_classifier/`.
- Run it against all conversations in `classifier/test_cases.py`, building
  cumulative `USER:` history per turn (just like the training data).
- Print overall accuracy and list any misclassified turns with their
  conversation name, turn index, expected vs predicted label, and the last
  user utterance.

You can tweak the decision threshold or max sequence length, for example:

```bash
python classifier/eval.py --threshold 0.3 --max-length 2048
```

---

### Pushing the model to Hugging Face Hub

Once you are happy with a trained checkpoint (for example the default one in
`classifier/models/longformer_screenshot_classifier/`), you can push it to a
Hugging Face Hub repo.

From the **repository root**:

```bash
HF_TOKEN=your_hf_token_here bash classifier/push.sh
```

This will:

- Activate `.venv_classifier`.
- Load the model + tokenizer from
  `classifier/models/longformer_screenshot_classifier/`.
- Create a simple `README.md` model card in that directory if one does not
  already exist.
- Push the model and tokenizer to the default repo
  `yapwithai/yap-function-caller`.

You can override the target repo or model directory, for example:

```bash
HF_TOKEN=your_hf_token_here bash classifier/push.sh \
  --model-dir classifier/models/longformer_screenshot_classifier_v2 \
  --repo-id your-org/your-custom-repo
```

If you already created a custom `README.md` inside the model directory and do
not want it overwritten, simply omit `--overwrite-readme` (the default). To
regenerate the README from the template in `push_to_hf.py`, pass
`--overwrite-readme`.

---

### Using the trained classifier elsewhere

Once you have a trained model in `classifier/models/longformer_screenshot_classifier/`,
you can load it from other code (e.g. your runtime server) roughly like this:

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_DIR = "classifier/models/longformer_screenshot_classifier"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

text = "USER: look at this amazing sunset"
inputs = tokenizer(
    text,
    return_tensors="pt",
    truncation=True,
    padding="max_length",
    max_length=1200,
)

# For Longformer, you typically assign global attention to the first token
attention_mask = inputs["attention_mask"]
import torch as _torch

global_attention_mask = _torch.zeros_like(attention_mask)
global_attention_mask[:, 0] = 1

outputs = model(
    **inputs,
    global_attention_mask=global_attention_mask,
)
probs = outputs.logits.softmax(dim=-1)

p_no, p_yes = probs[0].tolist()
print("P(no_screenshot)=", p_no)
print("P(take_screenshot)=", p_yes)
```

For production, you would:

- Build the same kind of **history string** you used for training
  (last N user messages, prefixed with `"USER:"`).
- Run the classifier once per latest user turn.
- Decide `True/False` by comparing `p_yes` to a threshold (e.g. 0.5 or tuned
  from validation data).

This directory is intentionally self-contained, so you can iterate on the
classifier independently of the main server config and then wire it in once
you are happy with its behavior and metrics.
