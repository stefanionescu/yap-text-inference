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

This model was quantized with [{quantizer_name}]({quantizer_link}) from {source_model_link}.

{hf_size_note}

## Quantization Overview
- Quantizer version: {quantizer_version}
- Scheme: {quant_scheme}
- Weights: {w_bit}-bit (group size {q_group_size}, zero-point {quant_zero_point})
- Targets: {quant_targets}
- Ignored modules: {quant_ignore}

## Calibration Data
- Dataset: {calibration_dataset_effective}
{calibration_samples_line}- Max sequence length: {calibration_seq_len}

## Runtime Recommendations
- Engine: {runtime_engine}
- KV cache dtype: {runtime_kv_cache_dtype}
- KV cache reuse: {runtime_kv_cache_reuse}
- Paged attention: {runtime_paged_attention}

### {quantizer_recipe_heading}
```json
{quant_summary}
```

## License

This quantized model inherits the license from the original base model: **{license_name}**

See the [original model's license]({license_link}) for full terms.
