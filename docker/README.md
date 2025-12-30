# Yap Text Inference Docker Setup

This Docker setup provides containerized deployment of Yap's text inference API with **pre-baked models**.

## Engine Options

Yap supports two inference engines:

| Engine | Best For | Requirements |
|--------|----------|--------------|
| **vLLM** | General use, AWQ/GPTQ models | Pre-quantized HuggingFace model |
| **TensorRT-LLM** | Maximum performance | Pre-built TRT engine from HuggingFace |

## Tag Naming Convention

All image tags **MUST** follow this naming convention:
- **vLLM images**: Tags must start with `vllm-` (e.g., `vllm-qwen30b-awq`)
- **TRT images**: Tags must start with `trt-` (e.g., `trt-qwen30b-sm90`)

The build will fail if the tag doesn't follow this convention.

## Contents

- [Quick Start](#quick-start)
- [vLLM Engine](#vllm-engine)
- [TensorRT-LLM Engine](#tensorrt-llm-engine)
- [Running Containers](#running-containers)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker with GPU support
- NVIDIA GPU with CUDA support
- Docker Hub account

### Build Commands

```bash
# vLLM - Pre-quantized AWQ model baked into image
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=vllm-qwen30b-awq \
  bash docker/build.sh

# TensorRT-LLM - Pre-built engine baked into image
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_REPO=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TAG=trt-qwen30b-sm90 \
  bash docker/build.sh
```

### Run

```bash
# Just run - model is already in the image!
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

---

## vLLM Engine

vLLM is recommended for most use cases. It supports pre-quantized AWQ and GPTQ models from HuggingFace.

### How It Works

1. **At build time**: The pre-quantized model is downloaded from HuggingFace and baked into the image
2. **At runtime**: The model is already there - the server starts immediately

### Supported Models

Chat models must be pre-quantized. The build validates that the model name contains one of:
- `awq` - AWQ quantized models
- `gptq` - GPTQ quantized models
- `w4a16`, `compressed-tensors`, `autoround` - llmcompressor W4A16 exports

### Build Examples

#### Chat-Only Image

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=vllm-qwen30b-awq \
  bash docker/build.sh
```

#### Tool-Only Image

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=tool \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=vllm-tool-only \
  bash docker/build.sh
```

#### Both Models

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=both \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=vllm-qwen3-full \
  bash docker/build.sh
```

### vLLM Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ENGINE` | Yes | Set to `vllm` |
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | Pre-quantized HF model (AWQ/GPTQ/W4A16) |
| `TOOL_MODEL` | If tool/both | Tool classifier from allowlist |
| `TAG` | Yes | Image tag (MUST start with `vllm-`) |
| `HF_TOKEN` | If private | HuggingFace token for private repos |

---

## TensorRT-LLM Engine

TensorRT-LLM provides maximum inference performance with pre-compiled engines.

### How It Works

1. **At build time**: The pre-built TRT engine is downloaded from HuggingFace and baked into the image
2. **At runtime**: The engine is already loaded - the server starts immediately

**Note:** The tool classifier always runs as a regular PyTorch model (not TRT). When deploying `tool` only, no TRT engine is needed.

### Requirements

For **chat** deployment (or **both**), you MUST specify:
1. **CHAT_MODEL**: HuggingFace TRT-quantized model repo (for tokenizer/checkpoint)
2. **TRT_ENGINE_REPO**: HuggingFace repo containing pre-built TRT engines
3. **TRT_ENGINE_LABEL**: Exact engine directory name in the repo

For **tool-only** deployment:
- Just specify `TOOL_MODEL` (no TRT engine required)

### Engine Label Format

The `TRT_ENGINE_LABEL` follows a specific naming convention:
```
sm{arch}_trt-llm-{version}_cuda{version}
```

Examples:
- `sm90_trt-llm-0.17.0_cuda12.8` - H100 GPU
- `sm89_trt-llm-0.17.0_cuda12.8` - L40S / RTX 4090
- `sm86_trt-llm-0.17.0_cuda12.8` - A100 / RTX 3090

### Build Examples

#### Chat-Only Image

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_REPO=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TAG=trt-qwen30b-sm90 \
  bash docker/build.sh
```

#### Tool-Only Image (No TRT Engine Required)

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=tool \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=trt-tool-only \
  bash docker/build.sh
```

#### Both Models (TRT Chat + PyTorch Tool Classifier)

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=both \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_REPO=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=trt-qwen3-full-sm90 \
  bash docker/build.sh
```

### TRT Engine Repo Structure

Your HuggingFace engine repo should contain:
```
your-engine-repo/
├── trt-llm/
│   ├── checkpoint/           # Tokenizer and config files
│   │   ├── config.json
│   │   ├── tokenizer.json
│   │   └── ...
│   └── engines/
│       ├── sm90_trt-llm-0.17.0_cuda12.8/   # H100
│       │   ├── rank0.engine
│       │   ├── config.json
│       │   └── ...
│       └── sm89_trt-llm-0.17.0_cuda12.8/   # L40S/4090
│           ├── rank0.engine
│           └── ...
```

### TRT Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ENGINE` | Yes | Set to `trt` |
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | HF repo for tokenizer/checkpoint |
| `TRT_ENGINE_REPO` | If chat/both | HF repo with pre-built engines |
| `TRT_ENGINE_LABEL` | If chat/both | Engine directory name (e.g., `sm90_trt-llm-0.17.0_cuda12.8`) |
| `TOOL_MODEL` | If tool/both | Tool classifier from allowlist |
| `TAG` | Yes | Image tag (MUST start with `trt-`) |
| `HF_TOKEN` | If private | HuggingFace token for private repos |

---

## Running Containers

### Basic Run

Since models are baked into the image, running is simple:

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

### With Resource Limits

```bash
docker run -d --gpus all --name yap-server \
  --memory=16g \
  --shm-size=2g \
  --ulimit memlock=-1:-1 \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

---

## Environment Variables

### Runtime Variables (All Engines)

| Variable | Required | Description |
|----------|----------|-------------|
| `TEXT_API_KEY` | Yes | API key for authentication |

### GPU Memory Allocation (Both Engines)

Memory allocation is consistent between vLLM and TRT deployments:

| Deploy Mode | Chat Model | Tool Classifier |
|-------------|------------|-----------------|
| `chat` only | 90% | - |
| `tool` only | - | 90% |
| `both` | 70% | 20% |

### vLLM-Specific Runtime

| Variable | Default | Description |
|----------|---------|-------------|
| `CHAT_GPU_FRAC` | 0.90 (single) / 0.70 (both) | GPU memory for chat model |
| `TOOL_GPU_FRAC` | 0.90 (single) / 0.20 (both) | GPU memory for tool classifier |
| `KV_DTYPE` | auto | KV cache dtype (fp8, int8, auto) |
| `VLLM_USE_V1` | 1 | Use vLLM V1 engine |

### TRT-Specific Runtime

| Variable | Default | Description |
|----------|---------|-------------|
| `TRT_KV_FREE_GPU_FRAC` | 0.90 (single) / 0.70 (both) | GPU fraction for TRT KV cache |
| `TOOL_GPU_FRAC` | 0.90 (single) / 0.20 (both) | GPU memory for tool classifier |
| `TRT_KV_ENABLE_BLOCK_REUSE` | 0 | Enable KV cache block reuse optimization |

---

## Health & Monitoring

### Health Check

```bash
curl http://localhost:8000/healthz
```

### View Logs

```bash
docker logs -f yap-server
```

### Container Stats

```bash
docker stats yap-server
```

---

## Troubleshooting

### vLLM Issues

1. **Build fails: "not a pre-quantized model"**
   - Chat model name must contain: `awq`, `gptq`, `w4a16`, `compressed-tensors`, or `autoround`

2. **Build fails: "not in the allowed list"**
   - Tool model must be in the allowlist in `src/config/models.py`

3. **Build fails: "TAG must start with 'vllm-'"**
   - All vLLM image tags must start with `vllm-`

### TRT Issues

1. **Runtime fails: "GPU ARCHITECTURE MISMATCH"**
   - The engine baked into the image was built for a different GPU
   - TRT engines are NOT portable across GPU architectures
   - Example: An engine built for H100 (`sm90`) won't work on L40S (`sm89`)
   - Solution: Use an image with an engine built for your GPU's SM architecture
   - Check your GPU's SM arch: `nvidia-smi --query-gpu=compute_cap --format=csv,noheader`

2. **Runtime fails: "MISSING ENGINE METADATA"**
   - The engine directory is missing `build_metadata.json`
   - Every TRT engine must have this file for GPU validation
   - Rebuild the engine with the latest quantization scripts

3. **Runtime fails: "CANNOT DETECT RUNTIME GPU"**
   - nvidia-smi not available or GPU not accessible
   - Ensure container runs with `--gpus all`
   - Verify GPU drivers are installed

4. **Build fails: "TRT_ENGINE_REPO is REQUIRED"**
   - You must specify both `TRT_ENGINE_REPO` and `TRT_ENGINE_LABEL` for chat/both modes

5. **Build fails: "TRT_ENGINE_LABEL has invalid format"**
   - Label must match: `sm{digits}_trt-llm-{version}_cuda{version}`
   - Example: `sm90_trt-llm-0.17.0_cuda12.8`

6. **Build fails: "No .engine files found"**
   - The specified `TRT_ENGINE_LABEL` directory doesn't exist in `TRT_ENGINE_REPO`
   - Verify the engine exists: `huggingface-cli repo-info yapwithai/qwen3-30b-trt-awq --files`

7. **Build fails: "TAG must start with 'trt-'"**
   - All TRT image tags must start with `trt-`

### Common Issues

1. **CUDA/GPU not available**
   - Ensure nvidia-docker is installed
   - Test: `docker run --gpus all nvidia/cuda:13.0.0-runtime-ubuntu24.04 nvidia-smi`

2. **Out of memory**
   - Reduce GPU fractions: `-e CHAT_GPU_FRAC=0.60`
   - Use int8 KV cache: `-e KV_DTYPE=int8`

3. **Build slow / large image**
   - Models are baked into the image, so build downloads the full model
   - Images will be large (10-50GB depending on model size)
   - Use Docker layer caching for faster rebuilds

### Debug Mode

```bash
docker run -it --gpus all --rm \
  -e TEXT_API_KEY=test \
  myuser/yap-text-api:vllm-qwen30b-awq \
  /bin/bash
```

---

## API Usage

Once running, the server provides:

- **Health**: `GET /healthz` (no auth required)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`

See the main README.md for complete API documentation.
