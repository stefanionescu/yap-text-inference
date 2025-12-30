#!/usr/bin/env bash
# Model and engine validation for Docker builds (TRT-LLM)
# 
# IMPORTANT: TRT Docker images require pre-built engines to be BAKED INTO the image.
# - TRT_ENGINE_REPO: HuggingFace repo containing pre-built engines
# - TRT_ENGINE_LABEL: Specific engine directory (e.g., sm90_trt-llm-0.17.0_cuda12.8)

# Allowed tool models (must match ALLOWED_TOOL_MODELS in src/config/models.py)
ALLOWED_TOOL_MODELS=(
    "yapwithai/yap-longformer-screenshot-intent"
    "yapwithai/yap-modernbert-screenshot-intent"
)

# POSIX-compatible lowercase function (works on macOS Bash 3.x)
to_lower() {
    echo "$1" | tr '[:upper:]' '[:lower:]'
}

# Check if model is a valid HuggingFace repo format
is_valid_hf_repo() {
    local model="$1"
    [[ -z "$model" ]] && return 1
    # Must contain "/" (HF repo format: owner/repo)
    [[ "$model" == *"/"* ]]
}

# Check if engine label is valid format (smXX_trt-llm-X.X.X_cudaX.X)
is_valid_engine_label() {
    local label="$1"
    [[ -z "$label" ]] && return 1
    # Must match pattern: sm{digits}_trt-llm-{version}_cuda{version}
    [[ "$label" =~ ^sm[0-9]+_trt-llm-[0-9]+\.[0-9]+.*_cuda[0-9]+\.[0-9]+$ ]]
}

# Validate chat model for TRT - must be a valid HF repo (used for tokenizer/checkpoint)
validate_chat_model() {
    local model="$1"
    if [[ -z "$model" ]]; then
        echo "[validate] CHAT_MODEL is required but not set" >&2
        return 1
    fi
    
    if ! is_valid_hf_repo "$model"; then
        echo "[validate] CHAT_MODEL '$model' is not a valid HuggingFace repo format (owner/repo)" >&2
        return 1
    fi
    
    echo "[validate] ✓ CHAT_MODEL: $model"
    return 0
}

# Validate TRT engine repo - REQUIRED for chat/both modes
validate_trt_engine_repo() {
    local repo="$1"
    
    if [[ -z "$repo" ]]; then
        echo "[validate] ✗ TRT_ENGINE_REPO is REQUIRED" >&2
        echo "[validate]   Pre-built engines must be baked into the Docker image" >&2
        echo "[validate]   Example: TRT_ENGINE_REPO=yapwithai/qwen3-30b-trt-awq" >&2
        return 1
    fi
    
    if ! is_valid_hf_repo "$repo"; then
        echo "[validate] TRT_ENGINE_REPO '$repo' is not a valid HuggingFace repo format (owner/repo)" >&2
        return 1
    fi
    
    echo "[validate] ✓ TRT_ENGINE_REPO: $repo"
    return 0
}

# Validate TRT engine label - REQUIRED for chat/both modes
validate_trt_engine_label() {
    local label="$1"
    
    if [[ -z "$label" ]]; then
        echo "[validate] ✗ TRT_ENGINE_LABEL is REQUIRED" >&2
        echo "[validate]   Specify the exact engine directory from the TRT_ENGINE_REPO" >&2
        echo "[validate]   Format: sm{arch}_trt-llm-{version}_cuda{version}" >&2
        echo "[validate]   Example: TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8" >&2
        return 1
    fi
    
    if ! is_valid_engine_label "$label"; then
        echo "[validate] ✗ TRT_ENGINE_LABEL '$label' has invalid format" >&2
        echo "[validate]   Expected: sm{arch}_trt-llm-{version}_cuda{version}" >&2
        echo "[validate]   Example: sm90_trt-llm-0.17.0_cuda12.8" >&2
        return 1
    fi
    
    echo "[validate] ✓ TRT_ENGINE_LABEL: $label"
    return 0
}

# Validate tool model - must be in allowlist
validate_tool_model() {
    local model="$1"
    if [[ -z "$model" ]]; then
        echo "[validate] TOOL_MODEL is required but not set" >&2
        return 1
    fi
    
    for allowed in "${ALLOWED_TOOL_MODELS[@]}"; do
        if [[ "$model" == "$allowed" ]]; then
            echo "[validate] ✓ TOOL_MODEL: $model"
            return 0
        fi
    done
    
    echo "[validate] TOOL_MODEL '$model' is not in the allowed list" >&2
    echo "[validate] See src/config/models.py for allowed tool models" >&2
    return 1
}

# Validate models based on deploy mode
validate_models_for_deploy() {
    local deploy_mode="$1"
    local chat_model="$2"
    local tool_model="$3"
    local trt_engine_repo="${4:-}"
    local trt_engine_label="${5:-}"
    local errors=0
    
    case "$deploy_mode" in
        chat)
            validate_chat_model "$chat_model" || ((errors++))
            validate_trt_engine_repo "$trt_engine_repo" || ((errors++))
            validate_trt_engine_label "$trt_engine_label" || ((errors++))
            ;;
        tool)
            validate_tool_model "$tool_model" || ((errors++))
            ;;
        both)
            validate_chat_model "$chat_model" || ((errors++))
            validate_trt_engine_repo "$trt_engine_repo" || ((errors++))
            validate_trt_engine_label "$trt_engine_label" || ((errors++))
            validate_tool_model "$tool_model" || ((errors++))
            ;;
        *)
            echo "[validate] Invalid DEPLOY_MODE: '$deploy_mode'. Must be chat|tool|both" >&2
            ((errors++))
            ;;
    esac
    
    return $errors
}

