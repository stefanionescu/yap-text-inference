# Yap Text Inference Docker Setup

Docker setup for Yap's text inference server with models baked into the image.

## Engine Options

The server supports two inference engines:

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

- [Engine Options](#engine-options)
- [Tag Naming Convention](#tag-naming-convention)
- [Quick Start](#quick-start)
- [vLLM Engine](#vllm-engine)
- [TensorRT-LLM Engine](#tensorrt-llm-engine)
- [Running Containers](#running-containers)
- [Environment Variables](#environment-variables)
- [Health & Monitoring](#health--monitoring)
- [Troubleshooting](#troubleshooting)
- [API Usage](#api-usage)

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
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TAG=trt-qwen30b-sm90 \
  bash docker/build.sh
```

### Run

```bash
# Just run - model is already in the image!
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -e MAX_CONCURRENT_CONNECTIONS=50 \
  -e CHAT_QUANTIZATION=awq \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

## vLLM Engine

vLLM works for most use cases. It supports pre-quantized AWQ and GPTQ models from HuggingFace.

### How It Works

1. **Build time**: Model downloaded from HuggingFace and baked into the image
2. **Runtime**: Server starts immediately with the baked-in model

### Supported Models

Chat models must be pre-quantized. Quantization is auto-detected from the model name (e.g. `awq`, `gptq`, `fp8`) or from `quantization_config.quant_method` in the model's `config.json`.

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

## TensorRT-LLM Engine

TensorRT-LLM provides better inference performance with pre-compiled engines.

### How It Works

1. **Build time**: TRT engine downloaded from HuggingFace and baked into the image
2. **Runtime**: Server starts immediately

The tool classifier always runs as PyTorch (not TRT). Tool-only deployments don't need a TRT engine.

### Requirements

For **chat** or **both**: specify `CHAT_MODEL` and `TRT_ENGINE_LABEL`.

For **tool-only**: just specify `TOOL_MODEL`.

### Engine Label Format

Format: `sm{arch}_trt-llm-{version}_cuda{version}`

Examples: `sm90_...` (H100), `sm89_...` (L40S/4090), `sm86_...` (A100/3090)

### Build Examples

#### Chat-Only Image

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
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
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=trt-qwen3-full-sm90 \
  bash docker/build.sh
```

### TRT Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ENGINE` | Yes | Set to `trt` |
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | HF repo for tokenizer/checkpoint |
| `TRT_ENGINE_REPO` | No | HF repo with pre-built engines (defaults to `CHAT_MODEL`) |
| `TRT_ENGINE_LABEL` | If chat/both | Engine directory name (e.g., `sm90_trt-llm-0.17.0_cuda12.8`) |
| `TOOL_MODEL` | If tool/both | Tool classifier from allowlist |
| `TAG` | Yes | Image tag (MUST start with `trt-`) |
| `HF_TOKEN` | If private | HuggingFace token for private repos |

## Running Containers

### Basic Run

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -e MAX_CONCURRENT_CONNECTIONS=50 \
  -e CHAT_QUANTIZATION=awq \
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
  -e MAX_CONCURRENT_CONNECTIONS=50 \
  -e CHAT_QUANTIZATION=awq \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

## Environment Variables

### Runtime Variables (All Engines)

| Variable | Required | Description |
|----------|----------|-------------|
| `TEXT_API_KEY` | Yes | API key for authentication |
| `MAX_CONCURRENT_CONNECTIONS` | Yes | Maximum concurrent WebSocket connections |
| `CHAT_QUANTIZATION` | Yes | Quantization type: `awq`, `gptq`, `fp8`, etc. Required since model paths don't contain quant info |

### GPU Memory Allocation (Both Engines)

Memory allocation:

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

## Troubleshooting

### vLLM Issues

1. **"not a pre-quantized model"** - Chat model name must contain `awq`, `gptq`, etc., or `config.json` must declare `quant_method`.
2. **"not in the allowed list"** - Tool model must be in `src/config/models.py`
3. **"TAG must start with 'vllm-'"** - Use the correct tag prefix

### TRT Issues

1. **"GPU ARCHITECTURE MISMATCH"** - Engine built for different GPU. TRT engines are not portable across architectures. Check: `nvidia-smi --query-gpu=compute_cap --format=csv,noheader`
2. **"MISSING ENGINE METADATA"** - Engine missing `build_metadata.json`. Rebuild.
3. **"CANNOT DETECT RUNTIME GPU"** - Run with `--gpus all`
4. **"TRT_ENGINE_REPO is not set"** - Set `CHAT_MODEL` (used as default) or `TRT_ENGINE_REPO` explicitly
5. **"TRT_ENGINE_LABEL has invalid format"** - Must match `sm{digits}_trt-llm-{version}_cuda{version}`
6. **"No .engine files found"** - Verify engine exists in repo
7. **"TAG must start with 'trt-'"** - Use correct tag prefix

### Common Issues

1. **CUDA/GPU not available** - Ensure nvidia-docker is installed. Test: `docker run --gpus all nvidia/cuda:13.0.0-runtime-ubuntu24.04 nvidia-smi`
2. **Out of memory** - Reduce fractions: `-e CHAT_GPU_FRAC=0.60` or use int8 KV: `-e KV_DTYPE=int8`
3. **Large image** - Models are baked in; images will be 10-50GB

### Debug Mode

```bash
docker run -it --gpus all --rm \
  -e TEXT_API_KEY=test \
  -e MAX_CONCURRENT_CONNECTIONS=10 \
  -e CHAT_QUANTIZATION=awq \
  myuser/yap-text-api:vllm-qwen30b-awq \
  /bin/bash
```

## API Usage

- **Health**: `GET /healthz` (no auth)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`
