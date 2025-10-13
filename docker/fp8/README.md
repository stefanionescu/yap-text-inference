# Yap Text Inference Docker Setup (FP8/GPTQ)

This Docker setup provides a containerized deployment of Yap's text inference API using automatic quantization selection between **FP8** (for float models) and **GPTQ** (for GPTQ repos), mirroring the behavior of `scripts/main.sh` from the root dir.

## Quick Start

### Prerequisites

- Docker with GPU support (nvidia-docker)
- NVIDIA GPU with CUDA support
- Chat and tool models on Hugging Face (float or GPTQ)

### Basic Usage

```bash
# Build the Docker image
DOCKER_USERNAME=yourusername ./build.sh

# Run (auto-detects quantization: GPTQ if chat repo contains 'GPTQ', else FP8)
YAP_TEXT_API_KEY=yap_token \
CHAT_MODEL=your-org/chat-model \
TOOL_MODEL=your-org/tool-model \
WARMUP_ON_START=0 \
CHAT_GPU_FRAC=0.70 \
TOOL_GPU_FRAC=0.20 \
  docker run -d --gpus all --name yap-server \
  -e YAP_TEXT_API_KEY -e CHAT_MODEL -e TOOL_MODEL \
  -e WARMUP_ON_START -e CHAT_GPU_FRAC -e TOOL_GPU_FRAC \
  -p 8000:8000 \
  yourusername/yap-text-inference-auto:latest
```

## Environment Variables

### Required
- `CHAT_MODEL`: Hugging Face repo for chat model (float or GPTQ)
- `TOOL_MODEL`: Hugging Face repo for tool model (float or GPTQ)

> Important: Both `CHAT_MODEL` and `TOOL_MODEL` must be provided for Docker deployments. This stack always deploys both models. `DEPLOY_MODELS` is ignored and effectively forced to `both` inside the Docker container.

### Optional
- `YAP_TEXT_API_KEY` (default: `yap_token`)
- `WARMUP_ON_START=0|1` (default: `0`)
- `CHAT_GPU_FRAC` (default: `0.70` when both models)
- `TOOL_GPU_FRAC` (default: `0.20` when both models)
- `DEPLOY_MODELS=both|chat|tool` (default: `both`)
- `CONCURRENT_MODEL_CALL=0|1` (default: `1`)
- `KV_DTYPE` is auto-selected; FP8 is preferred on Hopper/Ada when supported
- `QUANTIZATION` is auto-detected (GPTQ if chat repo contains 'GPTQ', else FP8)

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
  -e CHAT_MODEL=your-org/chat-model \
  -e TOOL_MODEL=your-org/tool-model \
  -e YAP_TEXT_API_KEY=yap_token \
  -e WARMUP_ON_START=0 \
  -e CHAT_GPU_FRAC=0.70 \
  -e TOOL_GPU_FRAC=0.20 \
  -p 8000:8000 \
  yourusername/yap-text-inference-auto:latest

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

## Advanced Configuration

### Resource Limits
```bash
docker run -d --gpus all --name yap-server \
  --memory=16g \
  --shm-size=2g \
  --ulimit memlock=-1:-1 \
  -e CHAT_MODEL=your-org/chat-model \
  -e TOOL_MODEL=your-org/tool-model \
  -p 8000:8000 \
  yourusername/yap-text-inference-auto:latest
```

### Persistent Cache Volumes
```bash
docker run -d --gpus all --name yap-server \
  -v yap-hf-cache:/app/.hf \
  -v yap-vllm-cache:/app/.vllm_cache \
  -e CHAT_MODEL=your-org/chat-model \
  -e TOOL_MODEL=your-org/tool-model \
  -p 8000:8000 \
  yourusername/yap-text-inference-auto:latest
```

## Troubleshooting

1. CUDA/GPU not available
   - Ensure nvidia-docker is installed
   - Check GPU visibility: `docker run --gpus all nvidia/cuda:12.8.0-runtime-ubuntu22.04 nvidia-smi`
2. Out of memory errors
   - Reduce GPU memory fractions: `CHAT_GPU_FRAC=0.60 TOOL_GPU_FRAC=0.15`
   - Try int8 KV cache: `KV_DTYPE=int8` (override only if needed)
3. Model loading failures
   - Verify model repo paths are correct
   - Check Hugging Face access permissions
4. Performance issues
   - Keep concurrent mode (default)
   - FP8 KV cache is selected automatically on supported GPUs
   - Prefer FlashInfer backend when available

## Advanced overrides (not recommended)

These are auto-selected; only override if you know why:

- `QUANTIZATION=fp8|gptq_marlin` — force mode instead of auto-detect
- `KV_DTYPE=auto|fp8|int8` — override KV cache dtype selection

## API Usage

Endpoints are identical to the non-Docker version:

- Health: `GET /healthz`
- Status: `GET /status` (requires API key)
- WebSocket: `ws://localhost:8000/ws?api_key=your_key`


