# Yap Text Inference Docker Setup

This Docker setup provides a containerized deployment of Yap's text inference API using **pre-quantized AWQ models**.

**Default Models:**
- **Chat**: [yapwithai/impish-12b-awq](https://huggingface.co/yapwithai/impish-12b-awq) - AWQ quantized Impish Nemo 12B
- **Tool**: [yapwithai/hammer-2.1-3b-awq](https://huggingface.co/yapwithai/hammer-2.1-3b-awq) - AWQ quantized Hammer 2.1 3B

## Quick Start

### Prerequisites

- Docker with GPU support (nvidia-docker)
- NVIDIA GPU with CUDA support
- Pre-quantized AWQ models on Hugging Face

### Basic Usage

```bash
# Build the Docker image
DOCKER_USERNAME=yourusername ./build.sh

docker run -d --gpus all --name yap-server \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
```

## Environment Variables

### AWQ Models (with defaults)
- `AWQ_CHAT_MODEL` - Hugging Face repo with pre-quantized AWQ chat model (default: `yapwithai/impish-12b-awq`)
- `AWQ_TOOL_MODEL` - Hugging Face repo with pre-quantized AWQ tool model (default: `yapwithai/hammer-2.1-3b-awq`)
- Override these to use your own pre-quantized AWQ models

### Optional (all have sensible defaults)
- `DEPLOY_MODELS=both|chat|tool` (default: both)
- `CONCURRENT_MODEL_CALL=0|1` (default: 1=concurrent)
- `YAP_API_KEY` (default: yap_token)
- `WARMUP_ON_START=0|1` (default: 1)
- `CHAT_GPU_FRAC=0.70` - GPU memory fraction for chat model
- `TOOL_GPU_FRAC=0.20` - GPU memory fraction for tool model
- `KV_DTYPE=fp8|int8|auto` (default: fp8 on supported GPUs)
- `VLLM_USE_V1=0|1` (default: 1)
- `VLLM_ATTENTION_BACKEND` (default: FLASHINFER on supported GPUs)

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

**Simple:**
```bash
docker run -d --gpus all --name yap-server \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest

# Check logs
docker logs -f yap-server
```

**Custom models:**
```bash
# Override with your own AWQ models
docker run -d --gpus all --name yap-server \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
```

Defaults mirror the host scripts' behavior (no baked AWQ model repos). Provide AWQ repos explicitly.

## Container Operations

### Starting the Server
```bash
docker run -d --gpus all --name yap-both \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -e CONCURRENT_MODEL_CALL=1 \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
```

### Chat Only
```bash
docker run -d --gpus all --name yap-chat \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e DEPLOY_MODELS=chat \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
```

### Tool Only
```bash
docker run -d --gpus all --name yap-tool \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -e DEPLOY_MODELS=tool \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
```

### Sequential Mode (Lower Resource Usage)
```bash
docker run -d --gpus all --name yap-sequential \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -e CONCURRENT_MODEL_CALL=0 \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
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
  yourusername/yap-text-inference:latest
```

### Custom GPU Memory Allocation
```bash
docker run -d --gpus all --name yap-server \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -e CHAT_GPU_FRAC=0.80 \
  -e TOOL_GPU_FRAC=0.15 \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
```

### Persistent Cache Volumes
```bash
docker run -d --gpus all --name yap-server \
  -v yap-hf-cache:/app/.hf \
  -v yap-vllm-cache:/app/.vllm_cache \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -p 8000:8000 \
  yourusername/yap-text-inference:latest
```

## Troubleshooting

### Common Issues

1. **CUDA/GPU not available**
   - Ensure nvidia-docker is installed
   - Check GPU visibility: `docker run --gpus all nvidia/cuda:12.8-runtime-ubuntu22.04 nvidia-smi`

2. **Out of memory errors**
   - Reduce GPU memory fractions: `CHAT_GPU_FRAC=0.60 TOOL_GPU_FRAC=0.15`
   - Use sequential mode: `CONCURRENT_MODEL_CALL=0`
   - Try int8 KV cache: `KV_DTYPE=int8`

3. **Model loading failures**
   - Verify AWQ model paths are correct
   - Check Hugging Face access permissions
   - Ensure models are properly quantized AWQ format

4. **Performance issues**
   - Enable concurrent mode: `CONCURRENT_MODEL_CALL=1`
   - Use fp8 KV cache on supported GPUs: `KV_DTYPE=fp8`
   - Try FlashInfer backend: `VLLM_ATTENTION_BACKEND=FLASHINFER`

### Debug Mode
```bash
docker run -it --gpus all --rm \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  yourusername/yap-text-inference:latest \
  /bin/bash
```

## Updates and Maintenance

### Update Container
```bash
docker pull yourusername/yap-text-inference:latest
docker stop yap-server
docker rm yap-server
# Run with new image
```

### Clean Up
```bash
# Remove container
docker stop yap-server && docker rm yap-server

# Remove image
docker rmi yourusername/yap-text-inference:latest

# Clean up volumes (careful!)
docker volume prune
```

## API Usage

Once running, the server provides the same API as the non-Docker version:

- **Health**: `GET /healthz` (no auth required)
- **Status**: `GET /status` (requires API key)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`

See the main README.md for complete API documentation.
