# vLLM Docker Image

vLLM inference image with models baked in.

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
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

## Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | Pre-quantized HF model (AWQ/GPTQ/W4A16) |
| `TOOL_MODEL` | If tool/both | Tool classifier HF repo |
| `TAG` | Yes | Image tag (must start with `vllm-`) |
| `HF_TOKEN` | If private | HuggingFace token |

## Runtime Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEXT_API_KEY` | Required | API key |
| `CHAT_GPU_FRAC` | 0.90 | GPU fraction for chat model |
| `TOOL_GPU_FRAC` | 0.20 | GPU fraction for tool classifier |
| `KV_DTYPE` | auto | KV cache dtype (fp8, int8, auto) |
| `VLLM_USE_V1` | 1 | Use vLLM V1 engine |

