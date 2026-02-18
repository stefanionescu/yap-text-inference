# Yap Text Inference Docker Setup

Docker setup for Yap's text inference server with models baked into the image.

## Contents

- [Engine Options](#engine-options)
- [Quick Start](#quick-start)
- [Tag Naming Convention](#tag-naming-convention)
- [Running Containers](#running-containers)
- [Environment Variables](#environment-variables)
- [Health & Monitoring](#health--monitoring)
- [API Usage](#api-usage)
- [Troubleshooting](#troubleshooting)
- [Stack Documentation](#stack-documentation)

## Engine Options

The server supports two inference engines:

| Engine | Best For | Requirements |
|--------|----------|--------------|
| **vLLM** | General use, AWQ/GPTQ models | Pre-quantized HuggingFace model |
| **TensorRT-LLM** | Maximum performance | Pre-built TRT engine from HuggingFace |

## Quick Start

### Prerequisites

- Docker with GPU support
- NVIDIA GPU with CUDA support
- Docker Hub account

### vLLM (Recommended)

vLLM works for most use cases and supports pre-quantized AWQ and GPTQ models from HuggingFace.

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=vllm-qwen30b-awq \
  bash docker/build.sh
```

See [vLLM README](vllm/README.md) for both-mode builds, quantization, and full variable reference.

### TensorRT-LLM

TensorRT-LLM provides better inference performance with pre-compiled engines.

> **GPU architecture must match.** TRT engines are compiled for a specific SM architecture (e.g., sm90 for H100). An image built for one architecture will not run on another. Check your GPU before building: `nvidia-smi --query-gpu=compute_cap --format=csv,noheader`

```bash
ENGINE=trt \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=yapwithai/qwen3-30b-trt-awq \
  TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8 \
  TAG=trt-qwen30b-sm90 \
  bash docker/build.sh
```

See [TRT README](trt/README.md) for both-mode builds, engine label format, GPU compatibility, and full variable reference.

### Tool-Only

Lightweight image with only the tool model -- no chat engine included.

```bash
DOCKER_USERNAME=myuser \
  DEPLOY_MODE=tool \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=tool-only \
  bash docker/build.sh
```

See [Tool README](tool/README.md) for details.

## Tag Naming Convention

Tags must use a prefix that matches the deploy mode:

| Deploy Mode | Engine | Required Prefix | Example |
|-------------|--------|-----------------|---------|
| `chat` / `both` | vLLM | `vllm-` | `vllm-qwen30b-awq` |
| `chat` / `both` | TRT | `trt-` | `trt-qwen30b-sm90` |
| `tool` | - | `tool-` | `tool-only` |

The build will fail if the tag doesn't match the required prefix.

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

### Debug Mode

Drop into a shell inside the container without starting the server:

```bash
docker run -it --gpus all --rm \
  -e TEXT_API_KEY=test \
  -e MAX_CONCURRENT_CONNECTIONS=10 \
  myuser/yap-text-api:vllm-qwen30b-awq \
  /bin/bash
```

## Environment Variables

### Runtime Variables (All Engines)

| Variable | Required | Description |
|----------|----------|-------------|
| `TEXT_API_KEY` | Yes | API key for authentication |
| `MAX_CONCURRENT_CONNECTIONS` | Yes | Maximum concurrent WebSocket connections |
| `CHAT_QUANTIZATION` | No | Override quantization (`awq`, `gptq`, `fp8`, etc.). Auto-detected by default |

For engine-specific variables, see the stack READMEs: [vLLM](vllm/README.md#runtime-variables) | [TRT](trt/README.md#runtime-variables) | [Tool](tool/README.md#runtime-variables)

### GPU Memory Allocation

Default memory fractions by deploy mode:

| Deploy Mode | Chat Model | Tool Model |
|-------------|------------|------------|
| `chat` only | 90% | - |
| `tool` only | - | 90% |
| `both` | 70% | 20% |

Override with `CHAT_GPU_FRAC` / `TRT_KV_FREE_GPU_FRAC` (chat) and `TOOL_GPU_FRAC` (tool).

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

## API Usage

- **Health**: `GET /healthz` (no auth required)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`

Health check example:

```bash
curl http://localhost:8000/healthz
```

WebSocket URL for client connections:

```
ws://localhost:8000/ws?api_key=your_secret_key
```

## Troubleshooting

### CUDA/GPU not available

**Symptom**: Container fails to start or reports no GPU.
**Cause**: nvidia-docker runtime not installed or `--gpus` flag missing.
**Fix**: Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) and run with `--gpus all`. Test with:

```bash
docker run --gpus all nvidia/cuda:13.0.0-runtime-ubuntu24.04 nvidia-smi
```

### Out of memory

**Symptom**: Server crashes or fails to load the model.
**Cause**: Model exceeds available GPU memory at the configured fraction.
**Fix**: Reduce GPU fractions (`-e CHAT_GPU_FRAC=0.60`) or use int8 KV cache (`-e KV_DTYPE=int8`).

### Large image size

**Symptom**: Image is 10-50 GB.
**Cause**: Models are baked into the image at build time. This is expected.
**Fix**: No action needed. The large size enables instant startup without runtime downloads.

### GPU architecture mismatch (TRT)

**Symptom**: `GPU ARCHITECTURE MISMATCH` error at startup.
**Cause**: The baked-in TRT engine was compiled for a different GPU architecture than the runtime GPU.
**Fix**: Check your GPU (`nvidia-smi --query-gpu=compute_cap --format=csv,noheader`) and rebuild with the correct `TRT_ENGINE_LABEL`. See [TRT GPU Compatibility](trt/README.md#gpu-compatibility).

### Model not allowlisted

**Symptom**: `not allowlisted for engine` or `not in the allowed list` at build time.
**Cause**: The model is not in the allowlist in `src/config`.
**Fix**: Use an allowlisted model, or provide a local model path.

### Tag prefix mismatch

**Symptom**: `TAG must start with 'vllm-'` / `'trt-'` / `'tool-'` at build time.
**Cause**: Tag does not match the required prefix for the engine/deploy mode.
**Fix**: Use the correct prefix. See [Tag Naming Convention](#tag-naming-convention).

### Engine metadata missing (TRT)

**Symptom**: `MISSING ENGINE METADATA` at startup.
**Cause**: Engine directory missing `build_metadata.json`.
**Fix**: Rebuild the TRT engine. See [TRT Troubleshooting](trt/README.md#troubleshooting).

### Engine label format invalid (TRT)

**Symptom**: `TRT_ENGINE_LABEL has invalid format` at build time.
**Cause**: Label doesn't match expected pattern.
**Fix**: Use format `sm{arch}_trt-llm-{version}_cuda{version}` (e.g., `sm90_trt-llm-0.17.0_cuda12.8`).

## Stack Documentation

| Stack | README |
|-------|--------|
| vLLM | [docker/vllm/README.md](vllm/README.md) |
| TensorRT-LLM | [docker/trt/README.md](trt/README.md) |
| Tool-Only | [docker/tool/README.md](tool/README.md) |
| Shared Utilities | [docker/common/README.md](common/README.md) |
