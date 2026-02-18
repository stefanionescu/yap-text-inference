#!/usr/bin/env bash
# =============================================================================
# TensorRT Script Configuration Values
# =============================================================================
# Canonical TRT defaults shared across shell scripts.

# shellcheck disable=SC2034
readonly CFG_TRT_REQUIRED_PYTHON_VERSION="3.10"
readonly CFG_TRT_VERSION="1.2.0rc5"
readonly CFG_TRT_PIP_PACKAGE="tensorrt_llm"
readonly CFG_TRT_EXTRA_INDEX_URL="https://pypi.nvidia.com"
readonly CFG_TRT_REPO_URL="https://github.com/Yap-With-AI/TensorRT-LLM.git"
readonly CFG_TRT_REPO_DIR_REL=".trtllm-repo"
readonly CFG_TRT_CLONE_DEPTH="1"
readonly CFG_TRT_CLONE_FILTER="blob:none"
readonly CFG_TRT_CLONE_ATTEMPTS="5"
readonly CFG_TRT_CLONE_BACKOFF_SECONDS="2"

# shellcheck disable=SC2034
readonly CFG_TRT_PYTORCH_VERSION="2.9.0+cu130"
readonly CFG_TRT_TORCHVISION_VERSION="0.24.0+cu130"
readonly CFG_TRT_TORCHAUDIO_VERSION="2.9.0+cu130"
readonly CFG_TRT_PYTORCH_INDEX_URL="https://download.pytorch.org/whl/cu130"
readonly CFG_TRT_TORCH_CONSTRAINTS_REL=".run/trt_torch_constraints.txt"

# shellcheck disable=SC2034
readonly CFG_MPI_VERSION_PIN="4.1.6-7ubuntu2"
readonly CFG_TRT_NEED_MPI="1"
readonly CFG_TRT_FP8_SM_ARCHS="sm89 sm90"
readonly CFG_TRT_DEFAULT_DTYPE="float16"
readonly CFG_TRT_DEFAULT_AWQ_BLOCK_SIZE="128"
readonly CFG_TRT_DEFAULT_CALIB_SIZE="64"
readonly CFG_TRT_DEFAULT_INPUT_LEN="5025"
readonly CFG_TRT_DEFAULT_OUTPUT_LEN="150"
readonly CFG_TRT_DEFAULT_CALIB_BATCH_SIZE="16"
readonly CFG_TRT_HEAVY_CALIB_BATCH_SIZE="8"
readonly CFG_TRT_DEFAULT_QFORMAT="int4_awq"
readonly CFG_TRT_DEFAULT_KV_CACHE_FP8="fp8"
readonly CFG_TRT_DEFAULT_KV_CACHE_INT8="int8"

# shellcheck disable=SC2034
readonly CFG_PIP_INSTALL_ATTEMPTS="5"
readonly CFG_PIP_INSTALL_BACKOFF_SECONDS="2"
