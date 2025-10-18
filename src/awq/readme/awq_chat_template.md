---
license: {license}
base_model: {base_model}
tags:
- awq
- quantized
- {w_bit}-bit
language:
- en
pipeline_tag: text-generation
---
 
# {model_name} — AWQ {w_bit}-bit

Clean, fast, memory‑efficient AWQ quantized chat model based on {source_model_link}.

## What it is
- Playful, expressive chat model with a classic Character AI vibe.
- Quantized with AWQ for smaller memory and faster inference.
- Drop-in for common text-generation stacks (Transformers, TGI, vLLM).

## Quick use (Transformers + AutoAWQ)
```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

model = AutoAWQForCausalLM.from_quantized("{repo_name}", trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained("{repo_name}", use_fast=True)
inputs = tokenizer("You are Impish. Say hi!", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=200)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

## Details
- Precision: {w_bit}-bit weights, group size {q_group_size}
- AWQ version: `{awq_version}`

### Quantization config
```json
{quant_summary}
```

### Calibration
{calib_section}

## Notes
- Apply your own safety/guardrails as needed.
- Target runtime & hardware: intended for vLLM on NVIDIA L40S. Not a TensorRT-LLM/TensorRT quantization.

## License
This model card inherits the license of the source model: {license}.
