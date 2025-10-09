---
license: {license}
license_name: {license_name}
license_link: {license_link}
base_model: {base_model}
tags:
- awq
- quantized
- {w_bit}-bit
- vllm
- yap-text-inference
- function-calling
- tool-use
language:
- en
pipeline_tag: text-generation
---

<div align="center">
  <h1 style="font-size: 48px; color: #E31515; font-weight: bold;">
    {model_name} - AWQ Quantized
  </h1>
  <p style="font-size: 18px; color: #666;">
    {w_bit}-bit AWQ quantization for function calling and tool use
  </p>
</div>

---

<div align="center">
  <img src="https://img.shields.io/badge/Quantization-AWQ-blue?style=for-the-badge" alt="AWQ">
  <img src="https://img.shields.io/badge/Precision-{w_bit}bit-green?style=for-the-badge" alt="{w_bit}-bit">
  <img src="https://img.shields.io/badge/Framework-vLLM-red?style=for-the-badge" alt="vLLM">
  <img src="https://img.shields.io/badge/Function_Calling-Enabled-orange?style=for-the-badge" alt="Function Calling">
</div>

---

## Tool Model Overview

This is an **AWQ quantized version** of {source_model_link}, specifically optimized for **function calling** and **tool use** with **vLLM** and other AWQ-compatible frameworks.

**Key Features:**
- **Function Calling**: Optimized for tool detection and structured output
- **Ultra-Fast**: Up to 3x faster inference for tool detection
- **Lightweight**: Minimal memory footprint for efficient deployment
- **Accurate**: High precision tool detection with minimal latency
- **Multi-Turn**: Supports complex multi-step function calling workflows

---

## Technical Specifications

| Specification | Details |
|---------------|---------|
| **Source Model** | {source_model_link} |
| **Model Type** | **Function Calling / Tool Use** |
| **Quantization Method** | AWQ (Activation-aware Weight Quantization) |
| **Precision** | {w_bit}-bit weights, 16-bit activations |
| **Group Size** | {q_group_size} |
| **AWQ Version** | `{awq_version}` |
| **Generated** | {generated_at} |
| **Pipeline** | AWQ Quantization |

### Performance Comparison

| Version | Size | Memory Usage | Inference Speed | Tool Detection |
|---------|------|--------------|----------------|----------------|
| Original FP16 | {original_size_gb} GB | ~{original_size_gb} GB VRAM | 1x | Baseline |
| **AWQ {w_bit}-bit** | **{quantized_size_gb} GB** | **~{quantized_size_gb} GB VRAM** | **~3x faster** | **Same accuracy** |

---

## Quick Start

### Using vLLM for Function Calling

```python
from vllm import LLM, SamplingParams

# Initialize the tool model
llm = LLM(
    model="{repo_name}",
    quantization="awq",
    trust_remote_code=True,
    max_model_len=2048,  # Tool models typically need less context
    gpu_memory_utilization=0.6,  # Tool models are more memory efficient
)

# Function calling example
tools = [
    {{
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {{
            "type": "object",
            "properties": {{
                "location": {{"type": "string", "description": "City name"}},
                "unit": {{"type": "string", "enum": ["celsius", "fahrenheit"]}}
            }},
            "required": ["location"]
        }}
    }}
]

# Tool detection prompt
prompt = "User: What's the weather in Paris?"
sampling_params = SamplingParams(temperature=0.1, max_tokens=100)

outputs = llm.generate([prompt], sampling_params)
print(outputs[0].outputs[0].text)
```

### Using with Python API

```python
# Direct integration with your inference pipeline
import requests
import json

# Example API call
response = requests.post("http://localhost:8001/v1/completions", 
    headers={{"Content-Type": "application/json"}},
    json={{
        "model": "{repo_name}",
        "prompt": "What's the weather like?",
        "max_tokens": 100,
        "tools": tools
    }}
)
```

### Production Server Deployment

```bash
# Deploy as tool detection service
vllm serve {repo_name} \
    --quantization awq \
    --host 0.0.0.0 \
    --port 8001 \
    --max-model-len 2048
```

---

## Quantization Details

{calib_section}

### Configuration

```json
{quant_summary}
```

**Tool Model Calibration:**
- **Method**: Activation-aware weight quantization with tool-specific data
- **Calibration Data**: Function calling and tool use examples
- **Optimization**: Optimized for structured output and JSON generation
- **Validation**: Tested against function calling benchmarks

---

## Advanced Configuration

### High-Throughput Tool Detection

```python
# Optimized for maximum tool detection throughput
llm = LLM(
    model="{repo_name}",
    quantization="awq",
    gpu_memory_utilization=0.8,
    max_model_len=1024,  # Shorter context for tool detection
    enforce_eager=False,  # Enable CUDA graphs for speed
)
```

### Multi-Model Deployment (Chat + Tool)

```python
# Deploy alongside chat model for complete pipeline
chat_llm = LLM(model="your-chat-model")
tool_llm = LLM(
    model="{repo_name}",
    quantization="awq",
    gpu_memory_utilization=0.3  # Share GPU with chat model
)
```

---

## Requirements & Compatibility

### System Requirements
- **GPU**: NVIDIA GPU with Compute Capability ≥ 7.5
- **VRAM**: Minimum {quantized_size_gb} GB (very lightweight!)
- **CUDA**: 11.8+ or 12.1+
- **Python**: 3.8+

### Framework Compatibility
- **vLLM** with function calling support
- **AutoAWQ** for local inference
- **Transformers** with tool calling templates
- **Custom inference pipelines**
- **OpenAI-compatible tool calling APIs**

---

## Troubleshooting

<details>
<summary><b>Tool Detection Issues</b></summary>

```python
# Ensure proper temperature settings for tool detection
sampling_params = SamplingParams(
    temperature=0.1,  # Low temperature for consistent tool calls
    top_p=0.9,
    max_tokens=100,   # Tools usually need short responses
    stop_token_ids=[your_stop_tokens]
)
```
</details>

<details>
<summary><b>JSON Parsing Errors</b></summary>

```python
# Use structured output settings
llm = LLM(
    model="{repo_name}",
    quantization="awq",
    guided_decoding_backend="outlines"  # For structured JSON
)
```
</details>

---

## Additional Resources

- **Original Model**: {source_model_link}
- **vLLM Tool Calling**: [https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#tool-calling](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#tool-calling)
- **AutoAWQ**: [https://github.com/casper-hansen/AutoAWQ](https://github.com/casper-hansen/AutoAWQ)

---

## License

This quantized model inherits the license from the original model: **{license_name}**

For more details, see the [original model license]({license_link}).

## Acknowledgments

- **Original Model**: Created by the team behind {original_author}
- **Quantization**: Powered by [AutoAWQ](https://github.com/casper-hansen/AutoAWQ)

