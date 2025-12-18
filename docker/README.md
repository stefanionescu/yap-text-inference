# Yap Text Inference Docker Setup

This Docker setup provides containerized deployment of Yap's text inference API with **pre-quantized models**.

## Engine Options

Yap supports two inference engines:

| Engine | Best For | Requirements |
|--------|----------|--------------|
| **vLLM** | General use, AWQ/GPTQ models | Pre-quantized HuggingFace model |
| **TensorRT-LLM** | Maximum performance | Pre-built TRT engine |

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
# vLLM (default) - for pre-quantized AWQ/GPTQ models
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=vllm-qwen30b \
  bash docker/build.sh

# TensorRT-LLM - for maximum performance with pre-built engines
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=Qwen/Qwen3-30B-A3B \
  TRT_ENGINE_REPO=myuser/qwen3-30b-trt-engine \
  TAG=trt-qwen30b \
  bash docker/build.sh
```

### Run

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

---

## vLLM Engine

vLLM is recommended for most use cases. It supports pre-quantized AWQ and GPTQ models from HuggingFace.

### Supported Models

Chat models must be pre-quantized. The build validates that the model name contains one of:
- `awq` - AWQ quantized models
- `gptq` - GPTQ quantized models
- `w4a16`, `nvfp4`, `compressed-tensors`, `autoround` - llmcompressor W4A16 exports

### Build Examples

#### Chat-Only Image

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=jeffcookio/Mistral-Small-3.2-24B-Instruct-2506-awq-sym \
  TAG=vllm-mistral-24b \
  bash docker/build.sh
```

#### Tool-Only Image

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=tool \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=vllm-tool \
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
| `TAG` | No | Custom tag (default: `vllm-<deploy_mode>`) |

---

## TensorRT-LLM Engine

TensorRT-LLM provides maximum inference performance with pre-compiled engines.

**Note:** The tool classifier always runs as a regular PyTorch model (not TRT). When deploying `tool` only, no TRT engine is needed. When deploying `both`, the chat model uses TRT while the tool classifier uses standard PyTorch.

### Requirements

For **chat** deployment (or **both**), you need:
1. **CHAT_MODEL**: HuggingFace model (used for tokenizer)
2. **TRT_ENGINE_REPO**: HuggingFace repo containing pre-built TRT engine
   - OR mount an engine directory at runtime

For **tool-only** deployment:
- Just specify `TOOL_MODEL` (no TRT engine required)

### Build Examples

#### With Engine Repo (Auto-Download)

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=Qwen/Qwen3-30B-A3B \
  TRT_ENGINE_REPO=myuser/qwen3-30b-trt-engine \
  TAG=trt-qwen30b \
  bash docker/build.sh
```

#### Without Engine Repo (Mount at Runtime)

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=Qwen/Qwen3-30B-A3B \
  TAG=trt-qwen30b-mount \
  bash docker/build.sh

# Run with mounted engine
docker run -d --gpus all --name yap-server \
  -v /path/to/trt-engine:/opt/engines/trt-chat \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:trt-qwen30b-mount
```

#### Tool-Only Image (No TRT Engine Required)

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=tool \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=trt-tool \
  bash docker/build.sh
```

#### Both Models (TRT Chat + PyTorch Tool Classifier)

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=both \
  CHAT_MODEL=Qwen/Qwen3-30B-A3B \
  TRT_ENGINE_REPO=myuser/qwen3-30b-trt-engine \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=trt-full \
  bash docker/build.sh
```

### TRT Engine Repo Structure

Your HuggingFace engine repo should contain:
```
your-engine-repo/
├── trt-llm/
│   └── engines/
│       └── sm89_trt-llm-1.2.0/   # SM arch + version
│           ├── rank0.engine
│           ├── config.json
│           └── ...
└── ... (or engines at root level)
```

The container auto-selects the engine matching your GPU's SM architecture.

### TRT Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ENGINE` | Yes | Set to `trt` |
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | HF model for tokenizer |
| `TRT_ENGINE_REPO` | Optional | HF repo with pre-built engines |
| `TOOL_MODEL` | If tool/both | Tool classifier from allowlist |
| `TAG` | No | Custom tag (default: `trt-<deploy_mode>`) |

---

## Running Containers

### Basic Run

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

### With Persistent Cache (Recommended)

```bash
# vLLM
docker run -d --gpus all --name yap-server \
  -v yap-cache:/app/.hf \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-tag

# TRT-LLM
docker run -d --gpus all --name yap-server \
  -v yap-cache:/app/.hf \
  -v yap-engines:/opt/engines \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:trt-tag
```

### With Resource Limits

```bash
docker run -d --gpus all --name yap-server \
  --memory=16g \
  --shm-size=2g \
  --ulimit memlock=-1:-1 \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

### Private Models

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -e HF_TOKEN=hf_xxxxx \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

---

## Environment Variables

### Runtime Variables (All Engines)

| Variable | Required | Description |
|----------|----------|-------------|
| `TEXT_API_KEY` | Yes | API key for authentication |
| `HF_TOKEN` | If private | HuggingFace token for private models |

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
| `TRT_KV_ENABLE_BLOCK_REUSE` | 1 | Enable KV cache block reuse |
| `TRT_ENGINE_DIR` | /opt/engines/trt-chat | Engine directory (for mounted engines) |

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
   - Chat model name must contain: `awq`, `gptq`, `w4a16`, `nvfp4`, `compressed-tensors`, or `autoround`

2. **Build fails: "not in the allowed list"**
   - Tool model must be in the allowlist in `src/config/models.py`

### TRT Issues

1. **Engine not found**
   - Ensure `TRT_ENGINE_REPO` is set, or mount engine at `/opt/engines/trt-chat`
   - Engine directory must contain `rank0.engine` and `config.json`

2. **SM architecture mismatch**
   - Engine must be built for your GPU's SM arch (e.g., sm89 for L40S)
   - Check available engines in your HF repo

### Common Issues

1. **CUDA/GPU not available**
   - Ensure nvidia-docker is installed
   - Test: `docker run --gpus all nvidia/cuda:13.0.0-runtime-ubuntu24.04 nvidia-smi`

2. **Out of memory**
   - Reduce GPU fractions: `-e CHAT_GPU_FRAC=0.60`
   - Use int8 KV cache: `-e KV_DTYPE=int8`

3. **Slow first start**
   - First run downloads model/engine from HuggingFace
   - Use persistent volumes for faster subsequent starts

### Debug Mode

```bash
docker run -it --gpus all --rm \
  -e TEXT_API_KEY=test \
  myuser/yap-text-api:your-tag \
  /bin/bash
```

---

## API Usage

Once running, the server provides:

- **Health**: `GET /healthz` (no auth required)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`

See the main README.md for complete API documentation.
