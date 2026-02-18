#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Shared Configuration
# =============================================================================
# Canonical TRT configuration used by install/quantize/build entrypoints.

_TRT_CONFIG_ROOT="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"

# TRT-LLM wheel and repository versioning
TRT_VERSION="${TRT_VERSION:-1.2.0rc5}"
TRT_PIP_SPEC="${TRT_PIP_SPEC:-tensorrt_llm==${TRT_VERSION}}"
TRT_EXTRA_INDEX_URL="${TRT_EXTRA_INDEX_URL:-https://pypi.nvidia.com}"

# TensorRT-LLM repository configuration
TRT_REPO_URL="${TRT_REPO_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}"
TRT_REPO_TAG="${TRT_REPO_TAG:-v${TRT_VERSION}}"
TRT_REPO_DIR="${TRT_REPO_DIR:-${_TRT_CONFIG_ROOT}/.trtllm-repo}"
TRT_CLONE_DEPTH="${TRT_CLONE_DEPTH:-1}"
TRT_CLONE_FILTER="${TRT_CLONE_FILTER:-blob:none}"
TRT_CLONE_ATTEMPTS="${TRT_CLONE_ATTEMPTS:-5}"
TRT_CLONE_BACKOFF_SECONDS="${TRT_CLONE_BACKOFF_SECONDS:-2}"

# Torch versions required by TRT-LLM 1.2.0rc5
TRT_PYTORCH_VERSION="${TRT_PYTORCH_VERSION:-2.9.0+cu130}"
TRT_TORCHVISION_VERSION="${TRT_TORCHVISION_VERSION:-0.24.0+cu130}"
TRT_PYTORCH_INDEX_URL="${TRT_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"

