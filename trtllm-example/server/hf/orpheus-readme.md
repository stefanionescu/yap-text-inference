---
license: {{license}}
base_model: {{base_model}}
tags:
- awq
- quantized
- {{w_bit}}-bit
- tensorrt-llm
- orpheus-tts
language:
- en
pipeline_tag: text-to-speech
---

<div align="center">
  <h1 style="font-size: 48px; color: #2E86AB; font-weight: bold;">
    {{model_name}} — INT{{w_bit}} AWQ Quantized
  </h1>
  <p style="font-size: 18px; color: #666;">
    Streaming optimized Orpheus 3B quant. Meant to run on {{gpu_name}} ({{gpu_vram_gb}} GB VRAM) with TensorRT-LLM
  </p>
</div>

---

<div align="center">
  <img src="https://img.shields.io/badge/Quantization-AWQ-blue?style=for-the-badge" alt="AWQ">
  <img src="https://img.shields.io/badge/Precision-INT{{w_bit}}-green?style=for-the-badge" alt="INT{{w_bit}}">
  <img src="https://img.shields.io/badge/Framework-TensorRT--LLM-red?style=for-the-badge" alt="TensorRT-LLM">
  <img src="https://img.shields.io/badge/License-Apache%202.0-yellow?style=for-the-badge" alt="License">
</div>

---

## Model Overview
This is a streaming optimized INT4 AWQ quantized version of {{source_model_link}}, meant to run with TensorRT-LLM.

**Key Features:**
- **Optimized for Production**: Built for high-throughput, low-latency TTS serving
- **Faster Inference**: Up to ~3x faster than FP16 with minimal perceived quality loss
- **Memory Efficient**: ≈4x smaller weights vs. FP16 (INT4)
- **Ready for Streaming**: Designed for real-time streaming TTS backends
- **Calibrated**: Calibrated for 48 tokens of input and up to 1162 tokens of output (roughly 14 seconds worth of audio per text chunk)

---

## Technical Specifications

| Specification | Details |
|---------------|---------|
| **Source Model** | {{source_model_link}} |
| **Quantization Method** | AWQ (Activation-aware Weight Quantization) |
| **Precision** | INT4 weights, INT8 KV cache |
| **AWQ Group/Block Size** | 128 |
| **TensorRT-LLM Version** | `{{tensorrt_llm_version}}` |
| **Max Batch Size** | {{max_batch_size}} |
| **SM Arch** | {{sm_arch}} |
| **GPU Name** | {{gpu_name}} |
| **GPU VRAM** | {{gpu_vram_gb}} GB |
| **CUDA Toolkit** | {{cuda_toolkit}} |
| **NVIDIA Driver** | {{nvidia_driver}} |
| **Generated** | {{generated_at}} |
| **Pipeline** | TensorRT-LLM AWQ Quantization |

### Artifact Layout

```
trt-llm/
  checkpoints/               # Quantized TRT-LLM checkpoints (portable)
    *.safetensors
    config.json
  engines/{{engine_label}}/  # Built TensorRT-LLM engines (hardware-specific)
    rank*.engine
    build_metadata.json
    build_command.sh
```

## Quantization Details

- Method: Activation-aware weight quantization (AWQ)
- Calibration size: 256
- AWQ block/group size: 128
- DType for build: float16


### Configuration Summary

```json
{{quant_summary}}
```

---

## Use Cases

- **Realtime Voice**: assistants, product demos, interactive agents
- **High-throughput Serving**: batch TTS pipelines, APIs
- **Edge & Cost-sensitive**: limited VRAM environments

---

## Advanced Configuration

- Max input length: tune `--max_input_len`
- Max output length: tune `--max_seq_len`
- Batch size: tune `--max_batch_size`
- Plugins: `--gpt_attention_plugin`, `--context_fmha`, `--paged_kv_cache`

---

## Requirements & Compatibility

### System Requirements
- **GPU**: NVIDIA, Compute Capability ≥ 8.0 (A100/RTX 40/H100 class recommended)
- **CUDA**: {{cuda_toolkit}}
- **Python**: 3.10+

### Framework Compatibility
- **TensorRT-LLM** (engines), version `{{tensorrt_llm_version}}`
- **TRT-LLM Checkpoints** are portable across systems; engines are not

### Installation

```bash
pip install huggingface_hub
# Install TensorRT-LLM per NVIDIA docs
# https://nvidia.github.io/TensorRT-LLM/
```

---

## Troubleshooting

<details>
<summary><b>Engine not portable</b></summary>
Engines are specific to GPU SM and TRT/CUDA versions. Rebuild on the target
system or download a matching `engines/sm80_trt-llm-1.2.0rc5_cuda13.0` variant if provided.
</details>

<details>
<summary><b>OOM or Slow Loading</b></summary>
Reduce `max_seq_len`, lower `max_batch_size`, and ensure `gpu_memory_utilization`
on your server is tuned to your GPU.
</details>

---

## Additional Resources

- **TensorRT-LLM Docs**: https://nvidia.github.io/TensorRT-LLM/
- **Activation-aware Weight Quantization (AWQ)**: https://github.com/mit-han-lab/llm-awq

---

## License

This quantized model inherits the license from the original model: **Apache 2.0**