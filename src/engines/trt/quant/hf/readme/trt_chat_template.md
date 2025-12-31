---
license: {{license}}
license_name: {{license_name}}
license_link: {{license_link}}
base_model: {{base_model}}
tags:
- tensorrt-llm
- quantized
- {{quant_method}}
- {{w_bit}}-bit
language:
- en
pipeline_tag: text-generation
---

# {{model_name}} — {{quant_method_upper}} (TensorRT-LLM)

This is a {{quant_method_upper}} quantized version of {{source_model_link}}, optimized for TensorRT-LLM inference.

---

## Model Overview

**Key Features:**
- **High-Performance Inference**: Optimized for NVIDIA GPUs with TensorRT-LLM
- **Memory Efficient**: {{w_bit}}-bit weights reduce VRAM usage vs FP16
- **Production Ready**: Built for low-latency, high-throughput chat serving
- **Portable Checkpoints**: Checkpoints work across systems; engines are hardware-specific

---

## Technical Specifications

| Specification | Details |
|---------------|---------|
| **Source Model** | {{source_model_link}} |
| **Quantization Method** | {{quant_method_upper}} |
| **Precision** | {{w_bit}}-bit weights |
| **KV Cache** | {{kv_cache_dtype}} |
| **Block/Group Size** | {{awq_block_size}} |
| **TensorRT-LLM Version** | `{{tensorrt_llm_version}}` (used for quantization) |
| **Max Batch Size** | {{max_batch_size}} |
| **Max Input Length** | {{max_input_len}} |
| **Max Output Length** | {{max_output_len}} |
| **SM Architecture** | {{sm_arch}} |
| **GPU** | {{gpu_name}} |
| **CUDA Toolkit** | {{cuda_toolkit}} |
| **Generated** | {{generated_at}} |

---

## Artifact Layout

```
trt-llm/
  checkpoints/
    *.safetensors
    config.json
  engines/{{engine_label}}/ 
    rank*.engine
    config.json
```

---

## Quantization Details

| Parameter | Value |
|-----------|-------|
| **Method** | {{quant_method_upper}} |
| **Calibration Size** | {{calib_size}} samples |
| **Calibration Seq Length** | {{calib_seqlen}} |
| **AWQ Block Size** | {{awq_block_size}} |
| **Calibration Batch Size** | {{calib_batch_size}} |

---

## Compatibility

### Requirements
- **GPU**: NVIDIA with Compute Capability ≥ {{min_compute_capability}} ({{gpu_arch_note}})
- **CUDA**: {{cuda_toolkit}}+
- **TensorRT-LLM**: `{{tensorrt_llm_version}}`
- **Python**: 3.10+

### Portability Notes
- **Checkpoints**: Portable across systems with compatible TensorRT-LLM versions; rebuild engines on the target GPU
- **Engines**: Hardware-specific (rebuild for different GPU/CUDA versions/SMs, e.g., H100/H200/B200/Blackwell, L40S, 4090/RTX)
- **{{quant_portability_note}}**

---

## Troubleshooting

<details>
<summary><b>Engine fails to load on different GPU</b></summary>
Engines are compiled for specific SM architecture and CUDA version. Either:

1. Use the checkpoints and rebuild the engine on your target system
2. Download an engine matching your GPU from the `engines/` subdirectories
</details>

<details>
<summary><b>Out of Memory</b></summary>
Reduce `max_batch_size` or `max_seq_len` when building the engine.
Adjust `kv_cache_config.free_gpu_memory_fraction` at runtime.
</details>

---

## Resources

- [TensorRT-LLM Documentation](https://nvidia.github.io/TensorRT-LLM/)
- [Source Model]({{source_model_link}})

---

## License

This quantized model inherits the license from the original base model: **{{license_name}}**

See the [original model's license]({{license_link}}) for full terms.


