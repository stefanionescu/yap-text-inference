# vLLM Docker Image

vLLM inference image with models baked in.
This stack is for vLLM chat deployments (`DEPLOY_MODE=chat|both`).
For tool-only images, use `docker/build.sh` with `DEPLOY_MODE=tool` (auto-routes to `docker/tool/build.sh`).

## Contents

- [Quick Start](#quick-start)
- [Build Variables](#build-variables)
- [Runtime Variables](#runtime-variables)

## Quick Start

### Build

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=vllm-qwen30b-awq \
  bash docker/build.sh
```

### Run

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -e MAX_CONCURRENT_CONNECTIONS=50 \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

## Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat` or `both` |
| `CHAT_MODEL` | If chat/both | Pre-quantized HF model (AWQ/GPTQ/W4A16) |
| `TOOL_MODEL` | If both | Tool model HF repo |
| `TAG` | Yes | Image tag (must start with `vllm-`) |
| `HF_TOKEN` | If private | HuggingFace token |

## Runtime Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEXT_API_KEY` | Yes | - | API key |
| `MAX_CONCURRENT_CONNECTIONS` | Yes | - | Maximum concurrent WebSocket connections |
| `CHAT_GPU_FRAC` | No | 0.90 | GPU fraction for chat model |
| `TOOL_GPU_FRAC` | No | 0.20 | GPU fraction for tool model |
| `KV_DTYPE` | No | auto | KV cache dtype (fp8, int8, auto) |
| `VLLM_USE_V1` | No | 1 | Use vLLM V1 engine |
