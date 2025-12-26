#!/usr/bin/env bash
# Model validation for Docker builds (TRT-LLM)
# Mirrors logic from src/config/quantization.py and src/config/models.py

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

# Validate chat model for TRT - must be a valid HF repo (used for tokenizer)
# The actual engine validation happens at runtime
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

# Validate TRT engine repo - must be a valid HF repo or empty (for mounted engines)
validate_trt_engine_repo() {
    local repo="$1"
    
    # Empty is OK - user will mount the engine
    if [[ -z "$repo" ]]; then
        echo "[validate] TRT_ENGINE_REPO not set - engine must be mounted at runtime"
        return 0
    fi
    
    if ! is_valid_hf_repo "$repo"; then
        echo "[validate] TRT_ENGINE_REPO '$repo' is not a valid HuggingFace repo format (owner/repo)" >&2
        return 1
    fi
    
    echo "[validate] ✓ TRT_ENGINE_REPO: $repo"
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
    local errors=0
    
    case "$deploy_mode" in
        chat)
            validate_chat_model "$chat_model" || ((errors++))
            validate_trt_engine_repo "$trt_engine_repo" || ((errors++))
            ;;
        tool)
            validate_tool_model "$tool_model" || ((errors++))
            ;;
        both)
            validate_chat_model "$chat_model" || ((errors++))
            validate_trt_engine_repo "$trt_engine_repo" || ((errors++))
            validate_tool_model "$tool_model" || ((errors++))
            ;;
        *)
            echo "[validate] Invalid DEPLOY_MODE: '$deploy_mode'. Must be chat|tool|both" >&2
            ((errors++))
            ;;
    esac
    
    return $errors
}

