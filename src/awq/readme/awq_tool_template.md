---
license: {license}
license_name: {license_name}
license_link: {license_link}
base_model: {base_model}
tags:
- awq
- quantized
- {w_bit}-bit
- function-calling
language:
- en
pipeline_tag: text-generation
---

# {model_name} — AWQ {w_bit}-bit (Tool Calling)

Compact tool-calling model quantized with AWQ, based on {source_model_link}.

## What it is
- Reliable function calling and structured outputs for your tools.
- Fast and memory‑efficient via AWQ.
- Not commercially friendly: check license before using in products.

## Quick use (Transformers + AutoAWQ)
```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

model = AutoAWQForCausalLM.from_quantized("{repo_name}", trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained("{repo_name}", use_fast=True)
prompt = "User: get current weather for Paris in celsius"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=120)
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
- Designed for function/tool calling; keep temperatures low for consistent JSON.
- Target runtime & hardware: intended for vLLM on NVIDIA L40S. Not a TensorRT-LLM/TensorRT quantization.

## License
- {license_name}
{license_link}
