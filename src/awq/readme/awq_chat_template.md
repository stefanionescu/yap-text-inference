---
license: {license}
license_name: {license}
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

This model was quantized with [{quantizer_name}]({quantizer_link}) from {source_model_link}.

## Quantization Overview
- Quantizer version: {quantizer_version}
- Scheme: {quant_scheme}
- Weights: {w_bit}-bit (group size {q_group_size}, zero-point {quant_zero_point})
- Targets: {quant_targets}
- Ignored modules: {quant_ignore}

## Calibration Data
- Dataset: {calibration_dataset_effective}
{calibration_samples_line}- Max sequence length: {calibration_seq_len}

### {quantizer_recipe_heading}
```json
{quant_summary}
```
