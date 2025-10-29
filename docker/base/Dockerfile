# Multi-stage build for a general-purpose base image
# - Can preload float/GPTQ or pre-quantized AWQ models at build-time
# - Can optionally quantize to AWQ at runtime if requested

FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0" \
    FORCE_CUDA=1 \
    MAX_JOBS=8

# System deps
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    git \
    wget \
    curl \
    gcc \
    g++ \
    make \
    cmake \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Create venv
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install Python deps
COPY requirements.txt /tmp/requirements.txt
RUN set -eux; \
    export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1 PIP_PREFER_BINARY=1 FLASHINFER_ENABLE_AOT=1; \
    TMP_REQ=/tmp/requirements.no_flashinfer.txt; \
    grep -v -E '^[[:space:]]*flashinfer-python([[:space:]]|$|==|>=|<=|~=|!=)' /tmp/requirements.txt > "${TMP_REQ}" || cp /tmp/requirements.txt "${TMP_REQ}" || true; \
    pip install --no-cache-dir -r "${TMP_REQ}"; \
    CUDA_NVVER="$(python -c 'import sys, torch; cu=(torch.version.cuda or "").strip(); sys.exit(1) if not cu else print(cu.replace(".", ""))' 2>/dev/null || true)"; \
    TORCH_MAJMIN="$(python -c 'import sys, torch; ver=torch.__version__.split("+",1)[0]; p=ver.split("."); print(p[0]+"."+p[1])' 2>/dev/null || true)"; \
    if [ -n "${CUDA_NVVER:-}" ] && [ -n "${TORCH_MAJMIN:-}" ]; then \
        FI_IDX="https://flashinfer.ai/whl/cu${CUDA_NVVER}/torch${TORCH_MAJMIN}"; \
        echo "[INFO] Installing flashinfer-python from ${FI_IDX}"; \
        pip install --no-cache-dir --prefer-binary --extra-index-url "${FI_IDX}" flashinfer-python || \
        (echo "[WARN] FlashInfer install via extra index failed, falling back to PyPI" && pip install --no-cache-dir --prefer-binary flashinfer-python || true); \
    else \
        echo "[WARN] Torch/CUDA not detected at build-time; attempting PyPI install for flashinfer-python"; \
        pip install --no-cache-dir --prefer-binary flashinfer-python || true; \
    fi

# Build-time preload controls for models
ARG PRELOAD_MODELS=0
ARG CHAT_MODEL=""
ARG TOOL_MODEL=""
ARG AWQ_CHAT_MODEL=""
ARG AWQ_TOOL_MODEL=""
ARG HF_TOKEN=""
ARG DEPLOY_MODELS=both

# Copy app code for preloading (vllm checks versions)
WORKDIR /app
COPY src/ /app/src/

# Ensure model directory exists regardless of preload flag (so we can copy it later)
RUN mkdir -p /app/models /app/.hf

# Preload Hugging Face models into image layers (optional)
# - Stored under /app/models/{chat,tool,chat_awq,tool_awq}
RUN PRELOAD_MODELS=${PRELOAD_MODELS} \
    DEPLOY_MODELS=${DEPLOY_MODELS} \
    CHAT_MODEL="${CHAT_MODEL}" \
    TOOL_MODEL="${TOOL_MODEL}" \
    AWQ_CHAT_MODEL="${AWQ_CHAT_MODEL}" \
    AWQ_TOOL_MODEL="${AWQ_TOOL_MODEL}" \
    HF_TOKEN="${HF_TOKEN}" \
    python - <<'PY'
import os
from pathlib import Path

# Only run when requested
if os.environ.get('PRELOAD_MODELS', '0') != '1':
    raise SystemExit(0)

Path('/app/models').mkdir(parents=True, exist_ok=True)
Path('/app/.hf').mkdir(parents=True, exist_ok=True)

from huggingface_hub import snapshot_download
from huggingface_hub.errors import HfHubHTTPError

hf_token = os.environ.get('HF_TOKEN', '')

def dl(repo_id: str, local_dir: str):
    if not repo_id:
        return
    print(f"[INFO] Preloading {repo_id} -> {local_dir}")
    Path(local_dir).mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(repo_id=repo_id, local_dir=local_dir, local_dir_use_symlinks=False, token=hf_token)
    except HfHubHTTPError as e:
        # Fail with a clear message only for auth errors; otherwise re-raise
        msg = str(e).lower()
        if '401' in msg or 'unauthorized' in msg:
            raise SystemExit("Unauthorized from Hugging Face. Provide HF_TOKEN or skip PRELOAD_MODELS=1.")
        raise

deploy = (os.environ.get('DEPLOY_MODELS') or 'both').lower()
chat = os.environ.get('CHAT_MODEL', '')
tool = os.environ.get('TOOL_MODEL', '')
awq_chat = os.environ.get('AWQ_CHAT_MODEL', '')
awq_tool = os.environ.get('AWQ_TOOL_MODEL', '')

if deploy in ('both', 'chat'):
    if awq_chat:
        dl(awq_chat, '/app/models/chat_awq')
    elif chat:
        dl(chat, '/app/models/chat')
if deploy in ('both', 'tool'):
    if awq_tool:
        dl(awq_tool, '/app/models/tool_awq')
    elif tool:
        dl(tool, '/app/models/tool')
PY


# ---- Runtime stage ----
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy venv
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy app code
COPY src/ /app/src/
COPY prompts/ /app/prompts/
COPY test/ /app/test/

# Copy preloaded models (if any)
COPY --from=builder /app/models /app/models

# Copy base docker scripts (build context provides ./scripts)
COPY scripts/ /app/scripts/

# Create runtime dirs and caches
RUN mkdir -p /app/logs /app/.run /app/.hf /app/.vllm_cache /app/models
RUN chmod +x /app/scripts/*.sh /app/scripts/common/*.sh /app/scripts/quantization/*.sh

# Cache directories
ENV HF_HOME=/app/.hf \
    HUGGINGFACE_HUB_CACHE=/app/.hf/hub \
    VLLM_CACHE_DIR=/app/.vllm_cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# Start
CMD ["/app/scripts/main.sh"]


