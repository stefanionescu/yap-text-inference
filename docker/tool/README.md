# Tool-Only Docker Image

Lightweight tool-only inference image with the tool model baked in. No chat engine is included.

Use this stack when you only need the tool model (e.g., screenshot intent classification) without a chat inference engine. This produces a much smaller image than the vLLM or TRT stacks. For chat deployments, see the [main Docker README](../README.md).

## Contents

- [Quick Start](#quick-start)
- [Build Variables](#build-variables)
- [Runtime Variables](#runtime-variables)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Build

```bash
DOCKER_USERNAME=myuser \
  DEPLOY_MODE=tool \
  TOOL_MODEL=yapwithai/yap-modernbert-screenshot-intent \
  TAG=tool-modernbert \
  bash docker/build.sh
```

### Run

```bash
docker run -d --gpus all --name yap-tool \
  -e TEXT_API_KEY=your_secret_key \
  -e MAX_CONCURRENT_CONNECTIONS=50 \
  -p 8000:8000 \
  myuser/yap-text-api:tool-modernbert
```

### Verify

```bash
curl http://localhost:8000/healthz
```

## Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `TOOL_MODEL` | Yes | Tool model HF repo |
| `TAG` | Yes | Image tag (must start with `tool-`) |
| `HF_TOKEN` | If private | HuggingFace token |

## Runtime Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEXT_API_KEY` | Yes | - | API key |
| `MAX_CONCURRENT_CONNECTIONS` | Yes | - | Maximum concurrent WebSocket connections |
| `TOOL_GPU_FRAC` | No | 0.90 | GPU fraction for tool model |

## Troubleshooting

For common issues (CUDA not available, OOM, large images), see [Troubleshooting](../README.md#troubleshooting) in the main Docker README.

**"TAG must start with 'tool-'"**: Tags for tool-only images must use the `tool-` prefix (e.g., `tool-modernbert`, `tool-only`).
