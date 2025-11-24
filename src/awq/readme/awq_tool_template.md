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
- Target runtime & hardware: intended for vLLM on NVIDIA L40S. Not a TensorRT-LLM/TensorRT quant.

## License
- {license_name}
{license_link}
