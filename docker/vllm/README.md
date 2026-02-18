# vLLM Docker Image

vLLM inference image with models baked in. This stack is for vLLM chat deployments (`DEPLOY_MODE=chat|both`).

For tool-only images, use `docker/build.sh` with `DEPLOY_MODE=tool` (auto-routes to `docker/tool/build.sh`).

For an overview of all stacks, see the [main Docker README](../README.md).

## Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Build Variables](#build-variables)
- [Runtime Variables](#runtime-variables)
- [Quantization](#quantization)
- [Troubleshooting](#troubleshooting)

## How It Works

1. **Build time**: The chat model (and optionally the tool model) is downloaded from HuggingFace and baked into the image.
2. **Runtime**: The server starts immediately with the baked-in model -- no downloads at startup.

## Quick Start

### Build (Chat-Only)

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=vllm-qwen30b-awq \
  bash docker/build.sh
```

### Build (Both Models)

Includes both the chat engine and the tool model in a single image:

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=both \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=vllm-qwen3-full \
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

### Verify

```bash
curl http://localhost:8000/healthz
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
| `CHAT_GPU_FRAC` | No | 0.90 (single) / 0.70 (both) | GPU fraction for chat model |
| `TOOL_GPU_FRAC` | No | 0.90 (single) / 0.20 (both) | GPU fraction for tool model |
| `KV_DTYPE` | No | auto | KV cache dtype (fp8, int8, auto) |
| `VLLM_USE_V1` | No | 1 | Use vLLM V1 engine |

## Quantization

Chat models must be pre-quantized. Quantization is auto-detected from the model name (e.g., `awq`, `gptq`, `fp8`) or from `quantization_config.quant_method` in the model's `config.json`.

To override auto-detection, set `CHAT_QUANTIZATION` at runtime:

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -e MAX_CONCURRENT_CONNECTIONS=50 \
  -e CHAT_QUANTIZATION=gptq \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

## Troubleshooting

For common issues (CUDA not available, OOM, large images), see [Troubleshooting](../README.md#troubleshooting) in the main Docker README.

**"not allowlisted for engine"**: The chat model must be in the allowlist for the vLLM engine (see `src/config`), or provide a local model path.

**"not in the allowed list"**: The tool model must be in the allowlist in `src/config/models.py`.

**"TAG must start with 'vllm-'"**: Tags for vLLM images must use the `vllm-` prefix (e.g., `vllm-qwen30b-awq`).

**Quantization not detected correctly**: Override with `-e CHAT_QUANTIZATION=awq` (or `gptq`, `fp8`, etc.) at runtime.
