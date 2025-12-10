# Multi-stage build for a general-purpose base image
# - Can preload float/GPTQ or pre-quantized AWQ models at build-time
# - Can optionally quantize to AWQ at runtime if requested

FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04 AS builder

# Allow overriding FlashInfer version at build time
ARG FLASHINFER_VERSION_SPEC="==0.5.2"
ARG LLMCOMPRESSOR_VERSION="0.8.1"
ENV FLASHINFER_VERSION_SPEC=${FLASHINFER_VERSION_SPEC}
ENV LLMCOMPRESSOR_VERSION=${LLMCOMPRESSOR_VERSION}

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
    ca-certificates \
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
    grep -v -E '^[[:space:]]*(flashinfer-python|llmcompressor)([[:space:]]|$|==|>=|<=|~=|!=)' /tmp/requirements.txt > "${TMP_REQ}" || cp /tmp/requirements.txt "${TMP_REQ}" || true; \
    pip install --no-cache-dir -r "${TMP_REQ}"; \
    CUDA_NVVER="$(python -c 'import sys, torch; cu=(torch.version.cuda or "").strip(); sys.exit(1) if not cu else print(cu.replace(".", ""))' 2>/dev/null || true)"; \
    TORCH_MAJMIN="$(python -c 'import sys, torch; ver=torch.__version__.split("+",1)[0]; p=ver.split("."); print(p[0]+"."+p[1])' 2>/dev/null || true)"; \
    if [ -n "${CUDA_NVVER:-}" ] && [ -n "${TORCH_MAJMIN:-}" ]; then \
        FI_IDX="https://flashinfer.ai/whl/cu${CUDA_NVVER}/torch${TORCH_MAJMIN}"; \
        FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:-==0.5.2}"; \
        echo "[INFO] Installing ${FI_PKG} from ${FI_IDX}"; \
        pip install --no-cache-dir --prefer-binary --extra-index-url "${FI_IDX}" "${FI_PKG}" || \
        (echo "[WARN] FlashInfer install via extra index failed, falling back to PyPI" && pip install --no-cache-dir --prefer-binary "${FI_PKG}" || true); \
    else \
        echo "[WARN] Torch/CUDA not detected at build-time; attempting PyPI install for FlashInfer with version spec"; \
        FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:-==0.5.2}"; \
        pip install --no-cache-dir --prefer-binary "${FI_PKG}" || true; \
    fi; \
    if [ -n "${LLMCOMPRESSOR_VERSION:-}" ]; then \
        echo "[INFO] Installing llmcompressor==${LLMCOMPRESSOR_VERSION} without deps"; \
        pip install --no-cache-dir --no-deps "llmcompressor==${LLMCOMPRESSOR_VERSION}"; \
    fi

ARG CHAT_MODEL=""
ARG TOOL_MODEL=""
ARG HF_TOKEN=""
ARG DEPLOY_MODELS=both

# Copy app code for preloading (vllm checks versions)
WORKDIR /app
COPY src/ /app/src/

# Ensure model directory exists regardless of preload flag (so we can copy it later)
RUN mkdir -p /app/models /app/.hf

# Preload Hugging Face models into image layers (always for embed-first design)
# - Stored under /app/models/{chat,tool,chat_awq}
RUN DEPLOY_MODELS=${DEPLOY_MODELS} \
    CHAT_MODEL="${CHAT_MODEL}" \
    TOOL_MODEL="${TOOL_MODEL}" \
    HF_TOKEN="${HF_TOKEN}" \
    python - <<'PY'
import os
from pathlib import Path
import sys

Path('/app/models').mkdir(parents=True, exist_ok=True)
Path('/app/.hf').mkdir(parents=True, exist_ok=True)

sys.path.insert(0, "/app")
from src.config.quantization import classify_prequantized_model
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
            raise SystemExit("Unauthorized from Hugging Face. Provide HF_TOKEN or ensure public access.")
        raise

deploy = (os.environ.get('DEPLOY_MODELS') or 'both').lower()
chat = os.environ.get('CHAT_MODEL', '').strip()
tool = os.environ.get('TOOL_MODEL', '').strip()

def classify(repo_id: str) -> str:
    if not repo_id:
        return ""
    return classify_prequantized_model(repo_id) or ""

def ensure_present(value: str, engine: str) -> None:
    if not value:
        raise SystemExit(f"Missing model for {engine}. Provide {engine.upper()}_MODEL at build time.")

if deploy in ('both', 'chat'):
    ensure_present(chat, 'chat')
    chat_kind = classify(chat)
    target = '/app/models/chat_awq' if chat_kind == 'awq' else '/app/models/chat'
    dl(chat, target)
    if chat_kind == 'awq':
        Path(target, '.awq_ok').write_text('preloaded\n', encoding='utf-8')
if deploy in ('both', 'tool'):
    ensure_present(tool, 'tool')
    tool_kind = classify(tool)
    if tool_kind == 'awq':
        raise SystemExit("Tool models are classifier-only; AWQ artifacts are not supported in mixed images.")
    target = '/app/models/tool'
    dl(tool, target)
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
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy venv
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy app code
COPY src/ /app/src/
COPY prompts/ /app/prompts/
COPY tests/ /app/tests/

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
    VLLM_CACHE_DIR=/app/.vllm_cache \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# Start
CMD ["/app/scripts/main.sh"]


