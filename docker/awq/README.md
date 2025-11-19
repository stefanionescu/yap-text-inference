# Yap Text Inference Docker Setup (AWQ)

This Docker setup provides a containerized deployment of Yap's text inference API using **pre-quantized AWQ models**.

**Default Models:**
- **Chat**: [yapwithai/impish-12b-awq](https://huggingface.co/yapwithai/impish-12b-awq) - AWQ quantized Impish Nemo 12B
- **Tool**: [yapwithai/hammer-2.1-3b-awq](https://huggingface.co/yapwithai/hammer-2.1-3b-awq) - AWQ quantized Hammer 2.1 3B

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
AWQ_CHAT_MODEL=your-org/chat-awq \
AWQ_TOOL_MODEL=your-org/tool-awq \
CHAT_GPU_FRAC=0.70 \
TOOL_GPU_FRAC=0.20 \
  docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY -e DEPLOY_MODELS \
  -e AWQ_CHAT_MODEL -e AWQ_TOOL_MODEL \
  -e CHAT_GPU_FRAC -e TOOL_GPU_FRAC \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:both

# Run (chat only)
docker run -d --gpus all --name yap-chat \
  -e DEPLOY_MODELS=chat \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:chat

# Run (tool only)
docker run -d --gpus all --name yap-tool \
  -e DEPLOY_MODELS=tool \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:tool
```

## Environment Variables

### Required
- `DEPLOY_MODELS` – `both|chat|tool` (default: `both`)
- If `DEPLOY_MODELS=chat`: `AWQ_CHAT_MODEL` (default: `yapwithai/impish-12b-awq`)
- If `DEPLOY_MODELS=tool`: `AWQ_TOOL_MODEL` (default: `yapwithai/hammer-2.1-3b-awq`)
- If `DEPLOY_MODELS=both`: `AWQ_CHAT_MODEL` and `AWQ_TOOL_MODEL`

### Optional
- `TEXT_API_KEY` (required, no default - must be set)
- `CHAT_GPU_FRAC` (default: `0.70`)
- `TOOL_GPU_FRAC` (default: `0.20`)

Engine/attention backend are auto-selected; no manual configuration required.

Note: This AWQ image now supports chat-only, tool-only, or both.

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

### Running the Container

```bash
docker run -d --gpus all --name yap-server \
  -e DEPLOY_MODELS=both \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
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

### Server Status (requires API key)
```bash
curl -H "X-API-Key: your_api_key" http://localhost:8000/status
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
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference-awq:latest
```

### Persistent Cache Volumes
```bash
docker run -d --gpus all --name yap-server \
  -v yap-hf-cache:/app/.hf \
  -v yap-vllm-cache:/app/.vllm_cache \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
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
   - Keep concurrent mode (default)
   - Use fp8 KV cache on supported GPUs: `KV_DTYPE=fp8`
   - Prefer FlashInfer backend when available

### Debug Mode
```bash
docker run -it --gpus all --rm \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
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
- **Status**: `GET /status` (requires API key)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`

See the main README.md for complete API documentation.
