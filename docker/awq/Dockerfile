# Multi-stage build for efficient Docker image
FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04 AS builder

# Allow overriding FlashInfer version at build time
ARG FLASHINFER_VERSION_SPEC=">=0.2.3,<0.3.2"
ARG LLMCOMPRESSOR_VERSION="0.8.1"
ENV FLASHINFER_VERSION_SPEC=${FLASHINFER_VERSION_SPEC}
ENV LLMCOMPRESSOR_VERSION=${LLMCOMPRESSOR_VERSION}

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"
ENV FORCE_CUDA=1
ENV MAX_JOBS=8

# Install system dependencies
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

# Create Python virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
# Install all requirements except flashinfer-python first, mirroring the scripts install flow
RUN set -eux; \
    export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1 PIP_PREFER_BINARY=1 FLASHINFER_ENABLE_AOT=1; \
    TMP_REQ=/tmp/requirements.no_flashinfer.txt; \
    grep -v -E '^[[:space:]]*(flashinfer-python|llmcompressor)([[:space:]]|$|==|>=|<=|~=|!=)' /tmp/requirements.txt > "${TMP_REQ}" || cp /tmp/requirements.txt "${TMP_REQ}" || true; \
    pip install --no-cache-dir -r "${TMP_REQ}"; \
    CUDA_NVVER="$(python -c 'import sys, torch; cu=(torch.version.cuda or "").strip(); sys.exit(1) if not cu else print(cu.replace(".", ""))' 2>/dev/null || true)"; \
    TORCH_MAJMIN="$(python -c 'import sys, torch; ver=torch.__version__.split("+",1)[0]; p=ver.split("."); print(p[0]+"."+p[1])' 2>/dev/null || true)"; \
    if [ -n "${CUDA_NVVER:-}" ] && [ -n "${TORCH_MAJMIN:-}" ]; then \
        FI_IDX="https://flashinfer.ai/whl/cu${CUDA_NVVER}/torch${TORCH_MAJMIN}"; \
        FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:->=0.2.3,<0.3.2}"; \
        echo "[INFO] Installing ${FI_PKG} from ${FI_IDX}"; \
        pip install --no-cache-dir --prefer-binary --extra-index-url "${FI_IDX}" "${FI_PKG}" || \
        (echo "[WARN] FlashInfer install via extra index failed, falling back to PyPI" && pip install --no-cache-dir --prefer-binary "${FI_PKG}" || true); \
    else \
        echo "[WARN] Torch/CUDA not detected at build-time; attempting PyPI install for FlashInfer with version spec"; \
        FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:->=0.2.3,<0.3.2}"; \
        pip install --no-cache-dir --prefer-binary "${FI_PKG}" || true; \
    fi; \
    if [ -n "${LLMCOMPRESSOR_VERSION:-}" ]; then \
        echo "[INFO] Installing llmcompressor==${LLMCOMPRESSOR_VERSION} without deps"; \
        pip install --no-cache-dir --no-deps "llmcompressor==${LLMCOMPRESSOR_VERSION}"; \
    fi

# Production stage
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

# Set environment variables for production
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory
WORKDIR /app

# Copy application code from build context
COPY src/ /app/src/
COPY prompts/ /app/prompts/
COPY scripts/ /app/scripts/

# Create necessary directories
RUN mkdir -p /app/logs /app/.run /app/.hf /app/.vllm_cache

# Set proper permissions
RUN chmod +x /app/scripts/*.sh

# Cache directories
ENV HF_HOME=/app/.hf
ENV HUGGINGFACE_HUB_CACHE=/app/.hf/hub
ENV VLLM_CACHE_DIR=/app/.vllm_cache
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["/app/scripts/main.sh"]
