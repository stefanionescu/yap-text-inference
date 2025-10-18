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

Source model: {source_model_link}

---

## Quick Start

### Using vLLM (Recommended)

```python
from vllm import LLM, SamplingParams

# Initialize the model
llm = LLM(
    model="{repo_name}",
    quantization="awq",
    trust_remote_code=True,
    max_model_len=4096,  # Adjust based on your needs
    gpu_memory_utilization=0.8,
)

# Generate text
prompts = ["The future of AI is"]
sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=200
)

outputs = llm.generate(prompts, sampling_params)
for output in outputs:
    print(output.outputs[0].text)
```

### Using Transformers + AutoAWQ

```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

# Load model and tokenizer
model = AutoAWQForCausalLM.from_quantized(
    "{repo_name}",
    fuse_layers=True,
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained("{repo_name}")

# Generate text
inputs = tokenizer("The future of AI is", return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=200, do_sample=True)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### Production Server Deployment

```bash
# Start vLLM server
vllm serve {repo_name} \
    --quantization awq \
    --host 0.0.0.0 \
    --port 8000
```

```python
# Client code
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key"
)

response = client.completions.create(
    model="{repo_name}",
    prompt="The future of AI is",
    max_tokens=200
)
```

---

## Quantization Details

{calib_section}

### Configuration

```json
{quant_summary}
```

**Calibration Process:**
- **Method**: Activation-aware weight quantization
- **Calibration Data**: High-quality, diverse text samples
- **Optimization**: Per-channel quantization for optimal quality
- **Validation**: Extensive testing against original model

---

## Advanced Configuration

### Memory Optimization

```python
# For maximum memory efficiency
llm = LLM(
    model="{repo_name}",
    quantization="awq", 
    gpu_memory_utilization=0.90,
    swap_space=4,  # GB
    enforce_eager=True
)
```

### Multi-GPU Setup

```python
# Tensor parallel across multiple GPUs
llm = LLM(
    model="{repo_name}",
    quantization="awq",
    tensor_parallel_size=2,  # Number of GPUs
    trust_remote_code=True
)
```

---

## Requirements & Compatibility

### System Requirements
- **GPU**: NVIDIA GPU with Compute Capability ≥ 7.5
- **VRAM**: Minimum {quantized_size_gb} GB
- **CUDA**: 11.8+ or 12.1+
- **Python**: 3.8+

### Framework Compatibility
- **vLLM** (`pip install vllm`)
- **AutoAWQ** (`pip install autoawq`)
- **Transformers** (with AutoAWQ backend)
- **Text Generation Inference** (TGI)
- **OpenAI-compatible APIs**

### Installation

```bash
# Install required packages
pip install vllm autoawq transformers torch

# For CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

---

## Troubleshooting

<details>
<summary><b>CUDA Out of Memory</b></summary>

```python
# Reduce memory usage
llm = LLM(
    model="{repo_name}",
    quantization="awq",
    gpu_memory_utilization=0.8,  # Reduce from 0.9
    max_model_len=2048,  # Reduce context length
    enforce_eager=True   # Disable CUDA graphs
)
```
</details>

<details>
<summary><b>Slow Loading</b></summary>

```python
# Enable model caching
import os
os.environ["HF_HUB_CACHE"] = "/path/to/cache"

# Or use local model path after first download
llm = LLM(model="/path/to/cached/model")
```
</details>

---

## Additional Resources

- **Original Model**: {source_model_link}
- **vLLM Documentation**: [https://docs.vllm.ai](https://docs.vllm.ai)
- **AutoAWQ**: [https://github.com/casper-hansen/AutoAWQ](https://github.com/casper-hansen/AutoAWQ)

---

## License

This quantized model inherits the license from the original model: **{license_name}**
