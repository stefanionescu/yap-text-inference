#!/usr/bin/env bash
# Model and engine validation for Docker builds (TRT-LLM)
#
# Uses Python validation module to ensure consistency with src/config.

# Validate models based on deploy mode using Python config
# Usage: validate_models_for_deploy <deploy_mode> <chat_model> <tool_model> [trt_engine_repo] [trt_engine_label]
validate_models_for_deploy() {
    local deploy_mode="$1"
    local chat_model="$2"
    local tool_model="$3"
    local trt_engine_repo="${4:-}"
    local trt_engine_label="${5:-}"
    
    # Try Python validation first (uses src/config as source of truth)
    if command -v python3 >/dev/null 2>&1; then
        local validate_script="${SCRIPT_DIR}/../../../common/download/validate.py"
        if [ -f "${validate_script}" ]; then
            DEPLOY_MODE="${deploy_mode}" \
            CHAT_MODEL="${chat_model}" \
            TOOL_MODEL="${tool_model}" \
            TRT_ENGINE_REPO="${trt_engine_repo}" \
            TRT_ENGINE_LABEL="${trt_engine_label}" \
            ENGINE="trt" \
            ROOT_DIR="${ROOT_DIR:-}" \
            python3 "${validate_script}"
            return $?
        fi
    fi
    
    # Fallback to shell validation if Python not available
    _validate_models_shell "$@"
}

# Shell fallback validation (for environments without Python)
_validate_models_shell() {
    local deploy_mode="$1"
    local chat_model="$2"
    local tool_model="$3"
    local trt_engine_repo="${4:-}"
    local trt_engine_label="${5:-}"
    local errors=0
    
    case "$deploy_mode" in
        chat)
            _validate_chat_model_shell "$chat_model" || ((errors++))
            _validate_trt_engine_repo_shell "$trt_engine_repo" || ((errors++))
            _validate_trt_engine_label_shell "$trt_engine_label" || ((errors++))
            ;;
        tool)
            _validate_tool_model_shell "$tool_model" || ((errors++))
            ;;
        both)
            _validate_chat_model_shell "$chat_model" || ((errors++))
            _validate_trt_engine_repo_shell "$trt_engine_repo" || ((errors++))
            _validate_trt_engine_label_shell "$trt_engine_label" || ((errors++))
            _validate_tool_model_shell "$tool_model" || ((errors++))
            ;;
        *)
            echo "[validate] Invalid DEPLOY_MODE: '$deploy_mode'. Must be chat|tool|both" >&2
            ((errors++))
            ;;
    esac
    
    return $errors
}

# Shell validation for chat model (TRT just needs valid HF repo)
_validate_chat_model_shell() {
    local model="$1"
    if [[ -z "$model" ]]; then
        echo "[validate] CHAT_MODEL is required but not set" >&2
        return 1
    fi
    
    if [[ "$model" != *"/"* ]]; then
        echo "[validate] CHAT_MODEL '$model' is not a valid HuggingFace repo format" >&2
        return 1
    fi
    
    echo "[validate] CHAT_MODEL: $model"
    return 0
}

# Shell validation for TRT engine repo
# Note: TRT_ENGINE_REPO defaults to CHAT_MODEL in build.sh
_validate_trt_engine_repo_shell() {
    local repo="$1"
    
    if [[ -z "$repo" ]]; then
        echo "[validate] ✗ TRT_ENGINE_REPO is not set and CHAT_MODEL is empty" >&2
        echo "[validate]   Set CHAT_MODEL (TRT_ENGINE_REPO defaults to it) or set TRT_ENGINE_REPO explicitly" >&2
        return 1
    fi
    
    if [[ "$repo" != *"/"* ]]; then
        echo "[validate] TRT_ENGINE_REPO '$repo' is not a valid HuggingFace repo format" >&2
        return 1
    fi
    
    return 0
}

# Shell validation for TRT engine label
_validate_trt_engine_label_shell() {
    local label="$1"
    
    if [[ -z "$label" ]]; then
        echo "[validate] ✗ TRT_ENGINE_LABEL is REQUIRED" >&2
        echo "[validate]   Format: sm{arch}_trt-llm-{version}_cuda{version}" >&2
        echo "[validate]   Example: TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8" >&2
        return 1
    fi
    
    # Pattern: sm{digits}_trt-llm-{version}_cuda{version}
    if [[ ! "$label" =~ ^sm[0-9]+_trt-llm-[0-9]+\.[0-9]+.*_cuda[0-9]+\.[0-9]+$ ]]; then
        echo "[validate] ✗ TRT_ENGINE_LABEL '$label' has invalid format" >&2
        echo "[validate]   Expected: sm{arch}_trt-llm-{version}_cuda{version}" >&2
        return 1
    fi
    
    echo "[validate] TRT_ENGINE_LABEL: $label"
    return 0
}

# Shell validation for tool model
_validate_tool_model_shell() {
    local model="$1"
    if [[ -z "$model" ]]; then
        echo "[validate] TOOL_MODEL is required but not set" >&2
        return 1
    fi
    
    # Allowed tool models (synced with src/config/models.py:ALLOWED_TOOL_MODELS)
    local allowed_models=(
        "yapwithai/yap-longformer-screenshot-intent"
        "yapwithai/yap-modernbert-screenshot-intent"
    )
    
    for allowed in "${allowed_models[@]}"; do
        if [[ "$model" == "$allowed" ]]; then
            echo "[validate] TOOL_MODEL: $model"
            return 0
        fi
    done
    
    echo "[validate] TOOL_MODEL '$model' is not in the allowed list" >&2
    echo "[validate] See src/config/models.py for allowed tool models" >&2
    return 1
}
