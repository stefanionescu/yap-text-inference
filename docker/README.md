# Yap Text Inference Docker Setup

This Docker setup provides a containerized deployment of Yap's text inference API with **pre-quantized models**.

**How it works:**
1. You build an image specifying which models it should use
2. When you run the container, it automatically downloads those specific models from HuggingFace
3. No model specification needed at runtime — just provide your API key

## Supported Models

### Chat Models
Chat models must be pre-quantized. The build validates that the model name contains one of:
- `awq` - AWQ quantized models
- `gptq` - GPTQ quantized models
- `w4a16`, `nvfp4`, `compressed-tensors`, `autoround` - llmcompressor W4A16 exports

### Tool Models
Tool models must be from the approved allowlist in `src/config/models.py`.

## Contents

- [Quick Start](#quick-start)
- [Build and Push](#build-and-push)
- [Running the Container](#running-the-container)
- [Environment Variables](#environment-variables)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker with GPU support
- NVIDIA GPU with CUDA support
- Docker Hub account

### Build and Run

```bash
# 1. Build and push image configured for your chat model
DOCKER_USERNAME=myuser \
  DEPLOY_MODELS=chat \
  CHAT_MODEL=jeffcookio/Mistral-Small-3.2-24B-Instruct-2506-awq-sym \
  TAG=mistral-24b \
  bash docker/build.sh

# 2. Run the container (model downloads automatically on first start)
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:mistral-24b
```

## Build and Push

### Chat-Only Image

```bash
DOCKER_USERNAME=myuser \
  DEPLOY_MODELS=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=qwen3-30b \
  bash docker/build.sh
```

### Tool-Only Image

```bash
DOCKER_USERNAME=myuser \
  DEPLOY_MODELS=tool \
  TOOL_MODEL=yapwithai/your-tool-model \
  TAG=tool \
  bash docker/build.sh
```

### Both Models Image

```bash
DOCKER_USERNAME=myuser \
  DEPLOY_MODELS=both \
  CHAT_MODEL=jeffcookio/Mistral-Small-3.2-24B-Instruct-2506-awq-sym \
  TOOL_MODEL=yapwithai/your-tool-model \
  TAG=mistral-full \
  bash docker/build.sh
```

### Build Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_USERNAME` | Yes | Your Docker Hub username |
| `IMAGE_NAME` | No | Docker image name (default: `yap-text-api`) |
| `DEPLOY_MODELS` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | Pre-quantized HF model (AWQ/GPTQ/W4A16) |
| `TOOL_MODEL` | If tool/both | Tool classifier from allowlist |
| `TAG` | No | Custom image tag (defaults to deploy mode) |
| `PLATFORM` | No | Target platform (default: `linux/amd64`) |

### Model Validation

The build will **fail** if:
- Chat model doesn't contain quantization markers (`awq`, `gptq`, `w4a16`, etc.)
- Tool model is not in the approved allowlist

## Running the Container

Models are configured at build time. Just run with your API key:

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

### With Persistent Cache (Recommended)

Mount a volume so models are cached between container restarts:

```bash
docker run -d --gpus all --name yap-server \
  -v yap-cache:/app/.hf \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

First run downloads the model. Subsequent runs start instantly from cache.

### Runtime Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TEXT_API_KEY` | Yes | API key for authentication |
| `HF_TOKEN` | If private | HuggingFace token for private models |
| `CHAT_GPU_FRAC` | No | GPU memory fraction for chat (default: 0.90 single, 0.70 both) |
| `TOOL_GPU_FRAC` | No | GPU memory fraction for tool (default: 0.90 single, 0.20 both) |

**Note:** You don't need to specify `CHAT_MODEL` or `TOOL_MODEL` at runtime — they're configured in the image.

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
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

### Private Models

For private HuggingFace models, pass `HF_TOKEN` at runtime:

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -e HF_TOKEN=hf_xxxxx \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

## Troubleshooting

### Common Issues

1. **Build fails: "not a pre-quantized model"**
   - Chat model name must contain: `awq`, `gptq`, `w4a16`, `nvfp4`, `compressed-tensors`, or `autoround`
   - Example valid names: `cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit`, `SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32`

2. **Build fails: "not in the allowed list"**
   - Tool model must be in the allowlist defined in `src/config/models.py`

3. **CUDA/GPU not available**
   - Ensure nvidia-docker is installed
   - Check GPU visibility: `docker run --gpus all nvidia/cuda:12.8.0-runtime-ubuntu22.04 nvidia-smi`

4. **Out of memory errors**
   - Reduce GPU memory fractions: `-e CHAT_GPU_FRAC=0.60`
   - Try int8 KV cache: `-e KV_DTYPE=int8`

5. **Slow first start**
   - First run downloads the model from HuggingFace
   - Use a persistent volume (`-v yap-cache:/app/.hf`) for instant subsequent starts

### Debug Mode
```bash
docker run -it --gpus all --rm \
  -e TEXT_API_KEY=test \
  myuser/yap-text-api:your-tag \
  /bin/bash
```

## Updates and Maintenance

### Update Container
```bash
# Pull latest image
docker pull myuser/yap-text-api:your-tag

# Replace running container
docker stop yap-server
docker rm yap-server
docker run -d --gpus all --name yap-server \
  -v yap-cache:/app/.hf \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:your-tag
```

### Clean Up
```bash
# Remove container
docker stop yap-server && docker rm yap-server

# Remove image
docker rmi myuser/yap-text-api:your-tag

# Clean up volumes
docker volume prune
```

## API Usage

Once running, the server provides:

- **Health**: `GET /healthz` (no auth required)
- **WebSocket**: `ws://localhost:8000/ws?api_key=your_key`

See the main README.md for complete API documentation.
