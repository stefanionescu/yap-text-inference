---
license: {license}
license_name: {license_name}
license_link: {license_link}
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

This chat model was quantized with [LLM Compressor](https://github.com/vllm-project/llm-compressor) using `{awq_version}` from {source_model_link}. The export is ready to run in `vllm` with `quantization="compressed-tensors"`/`"awq_marlin"` when applicable.

## Quantization Overview
- Pipeline: {pipeline_name}
- Compressor version: {llmcompressor_version}
- Scheme: {quant_scheme}
- Weights: {w_bit}-bit (group size {q_group_size}, zero-point {quant_zero_point})
- Targets: {quant_targets}
- Ignored modules: {quant_ignore}

## Calibration Data
- Requested dataset: {calibration_dataset_requested}
- Effective dataset: {calibration_dataset_effective}
- Samples: {calibration_samples}
- Max sequence length: {calibration_seq_len}
- Profiled model type: {calibration_model_type}

### llmcompressor recipe
```json
{quant_summary}
```

### Calibration notes
{calib_section}

## License
This quantization inherits {license_name}. {license_link}
