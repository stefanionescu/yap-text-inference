# Yap Text Inference Docker Setup (AWQ)

This Docker setup provides a containerized deployment of Yap's text inference API using **pre-quantized AWQ models**.  
All artifacts are produced with [`llmcompressor`](https://github.com/vllm-project/llm-compressor) (or [AutoAWQ 0.2.9](https://github.com/AutoAWQ/AutoAWQ) for Qwen2/Qwen3 and Mistral 3 families) and ship as **W4A16 compressed-tensor exports**, so vLLM automatically selects the Marlin kernels (you will see `quantization=compressed-tensors` in the server logs even though `QUANTIZATION=awq` is configured).

**Default Models:**
- **Chat**: [cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit](https://huggingface.co/cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit) - AWQ quantized Qwen3 30B-A3B
- **Tool**: [yapwithai/yap-longformer-screenshot-intent](https://huggingface.co/yapwithai/yap-longformer-screenshot-intent) - Screenshot intent classifier (float)

## Contents

- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Basic Usage](#basic-usage)
- [Environment Variables](#environment-variables)
  - [Required](#required)
  - [Optional](#optional)
- [Build and Deploy](#build-and-deploy)
  - [Building the Image](#building-the-image)
  - [Running the Container](#running-the-container)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
  - [Health Check](#health-check)
  - [Server Status (requires API key)](#server-status-requires-api-key)
  - [View Logs](#view-logs)
  - [Container Stats](#container-stats)
- [Advanced Configuration](#advanced-configuration)
  - [Resource Limits](#resource-limits)
  - [Persistent Cache Volumes](#persistent-cache-volumes)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Debug Mode](#debug-mode)
- [Updates and Maintenance](#updates-and-maintenance)
  - [Update Container](#update-container)
  - [Clean Up](#clean-up)
- [API Usage](#api-usage)

## Quick Start

### Prerequisites

- Docker with GPU support (nvidia-docker)
- NVIDIA GPU with CUDA support
- Pre-quantized AWQ models on Hugging Face

### Basic Usage

```bash
# Build the Docker image (tag auto-set by DEPLOY_MODELS)
DOCKER_USERNAME=yourusername DEPLOY_MODELS=both ./build.sh  # tag :both
DOCKER_USERNAME=yourusername DEPLOY_MODELS=chat ./build.sh  # tag :chat
DOCKER_USERNAME=yourusername DEPLOY_MODELS=tool ./build.sh  # tag :tool

# Run (deploy both models)
TEXT_API_KEY=your_secret_key \
DEPLOY_MODELS=both \
CHAT_MODEL=your-org/chat-awq \
TOOL_MODEL=your-org/tool-classifier \
CHAT_GPU_FRAC=0.70 \
TOOL_GPU_FRAC=0.20 \
  docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY -e DEPLOY_MODELS \
  -e CHAT_MODEL -e TOOL_MODEL \
  -e CHAT_GPU_FRAC -e TOOL_GPU_FRAC \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:both

# Run (chat only)
docker run -d --gpus all --name yap-chat \
  -e DEPLOY_MODELS=chat \
  -e CHAT_MODEL=your-org/chat-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:chat

# Run (tool only)
docker run -d --gpus all --name yap-tool \
  -e DEPLOY_MODELS=tool \
  -e TOOL_MODEL=your-org/tool-classifier \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:tool

## Environment Variables

### Required
- `TEXT_API_KEY` – API key handed to the server
- `DEPLOY_MODELS` – `both|chat|tool` (default: `both`)
- If `DEPLOY_MODELS=chat`: `CHAT_MODEL` (default: `cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit`)
- If `DEPLOY_MODELS=tool`: `TOOL_MODEL` (default: `yapwithai/yap-longformer-screenshot-intent`)
- If `DEPLOY_MODELS=both`: `CHAT_MODEL` and `TOOL_MODEL`

### Optional
- `CHAT_GPU_FRAC` (default: `0.70` when `DEPLOY_MODELS=both`, `0.90` otherwise)
- `TOOL_GPU_FRAC` (default: `0.20` when `DEPLOY_MODELS=both`, `0.90` otherwise; caps classifier GPU allocations)

Engine/attention backend and the precise quantization backend are auto-selected; whether the model path is local or a Hugging Face repo ID, the container inspects `quantization_config.json` and tells vLLM to use the correct backend (`compressed-tensors` for llmcompressor exports). Make sure `HF_TOKEN` / `HUGGINGFACE_HUB_TOKEN` is set if you pull private repos.

Note: This AWQ image now supports chat-only, tool-only, or both deployments.

## Build and Deploy

### Building the Image

```bash
# Basic build and push
DOCKER_USERNAME=yourusername ./build.sh

# Build only (no push)
./build.sh --build-only

# Multi-platform build
./build.sh --multi-platform

# Build with custom tag
TAG=v1.0.0 ./build.sh
```

> **llmcompressor pin:** The Dockerfile installs `llmcompressor==0.8.1` with `--no-deps` so it remains compatible with `torch==2.9.0`. Override via `LLMCOMPRESSOR_VERSION=... ./build.sh` if you need a different release, but keep the manual install pattern. Qwen-family and Mistral 3 exports automatically use AutoAWQ (pinned to `autoawq==0.2.9` in `requirements.txt`) because llmcompressor cannot trace their hybrid forward graphs yet.

### Running the Container

```bash
docker run -d --gpus all --name yap-server \
  -e DEPLOY_MODELS=both \
  -e CHAT_MODEL=your-org/chat-awq \
  -e TOOL_MODEL=your-org/tool-classifier \
  -e TEXT_API_KEY=your_secret_key \
  -e CHAT_GPU_FRAC=0.70 \
  -e TOOL_GPU_FRAC=0.20 \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:latest

# Check logs
docker logs -f yap-server
```

## Monitoring and Health Checks

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

## Advanced Configuration

### Resource Limits
```bash
docker run -d --gpus all --name yap-server \
  --memory=16g \
  --shm-size=2g \
  --ulimit memlock=-1:-1 \
  -e CHAT_MODEL=your-org/chat-awq \
  -e TOOL_MODEL=your-org/tool-classifier \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:latest
```

### Persistent Cache Volumes
```bash
docker run -d --gpus all --name yap-server \
  -v yap-hf-cache:/app/.hf \
  -v yap-vllm-cache:/app/.vllm_cache \
  -e CHAT_MODEL=your-org/chat-awq \
  -e TOOL_MODEL=your-org/tool-classifier \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:latest
```

## Troubleshooting

### Common Issues

1. **CUDA/GPU not available**
   - Ensure nvidia-docker is installed
   - Check GPU visibility: `docker run --gpus all nvidia/cuda:12.8.0-runtime-ubuntu22.04 nvidia-smi`

2. **Out of memory errors**
   - Reduce GPU memory fractions: `CHAT_GPU_FRAC=0.60 TOOL_GPU_FRAC=0.15`
   - Try int8 KV cache: `KV_DTYPE=int8`

3. **Model loading failures**
   - Verify AWQ model paths are correct
   - Check Hugging Face access permissions
   - Ensure models are properly quantized AWQ format

4. **Performance issues**
   - Sequential execution is always enabled; validate tool routing before chat
   - Use fp8 KV cache on supported GPUs: `KV_DTYPE=fp8`
   - Prefer FlashInfer backend when available

### Debug Mode
```bash
docker run -it --gpus all --rm \
  -e CHAT_MODEL=your-org/chat-awq \
  -e TOOL_MODEL=your-org/tool-classifier \
  yourusername/yap-text-inference-awq:latest \
  /bin/bash
```

## Updates and Maintenance

### Update Container
```bash
docker pull yourusername/yap-text-inference-awq:both
docker stop yap-server
docker rm yap-server
# Run with new image
```

### Clean Up
```bash
# Remove container
docker stop yap-server && docker rm yap-server

# Remove image
docker rmi yourusername/yap-text-inference-awq:latest

# Clean up volumes (careful!)
docker volume prune
```

## API Usage

Once running, the server provides the same API as the non-Docker version:

- **Health**: `GET /healthz` (no auth required)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`

See the main README.md for complete API documentation.
