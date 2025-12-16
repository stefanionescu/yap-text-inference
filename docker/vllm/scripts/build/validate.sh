#!/usr/bin/env bash
# Model validation for Docker builds (vLLM)
# Mirrors logic from src/config/quantization.py and src/config/models.py

# Allowed tool models (must match ALLOWED_TOOL_MODELS in src/config/models.py)
ALLOWED_TOOL_MODELS=(
    "yapwithai/yap-longformer-screenshot-intent"
    "yapwithai/yap-modernbert-screenshot-intent"
)

# W4A16 marker hints (from src/config/quantization.py)
W4A16_HINTS=("w4a16" "nvfp4" "compressed-tensors" "autoround")

# POSIX-compatible lowercase function (works on macOS Bash 3.x)
to_lower() {
    echo "$1" | tr '[:upper:]' '[:lower:]'
}

# Check if a model name indicates AWQ quantization
is_awq_model_name() {
    local model="$1"
    [[ -z "$model" ]] && return 1
    # Must contain "/" (HF repo format) and "awq" (case insensitive)
    local lowered
    lowered=$(to_lower "$model")
    [[ "$model" == *"/"* ]] && [[ "$lowered" == *"awq"* ]]
}

# Check if a model name indicates GPTQ quantization
is_gptq_model_name() {
    local model="$1"
    [[ -z "$model" ]] && return 1
    local lowered
    lowered=$(to_lower "$model")
    [[ "$model" == *"/"* ]] && [[ "$lowered" == *"gptq"* ]]
}

# Check if model name contains W4A16-style markers
has_w4a16_marker() {
    local model="$1"
    [[ -z "$model" ]] && return 1
    local lowered
    lowered=$(to_lower "$model")
    for marker in "${W4A16_HINTS[@]}"; do
        [[ "$lowered" == *"$marker"* ]] && return 0
    done
    return 1
}

# Check if model is pre-quantized (AWQ, GPTQ, or W4A16)
is_prequantized_model() {
    local model="$1"
    is_awq_model_name "$model" || is_gptq_model_name "$model" || has_w4a16_marker "$model"
}

# Classify the quantization type
classify_prequantized_model() {
    local model="$1"
    if is_awq_model_name "$model" || has_w4a16_marker "$model"; then
        echo "awq"
    elif is_gptq_model_name "$model"; then
        echo "gptq"
    else
        echo ""
    fi
}

# Validate chat model - must be pre-quantized
validate_chat_model() {
    local model="$1"
    if [[ -z "$model" ]]; then
        echo "[ERROR] CHAT_MODEL is required but not set" >&2
        return 1
    fi
    
    if ! is_prequantized_model "$model"; then
        echo "[ERROR] CHAT_MODEL '$model' is not a pre-quantized model" >&2
        echo "[ERROR] Chat model name must contain one of: awq, gptq, w4a16, nvfp4, compressed-tensors, autoround" >&2
        return 1
    fi
    
    local quant_type
    quant_type=$(classify_prequantized_model "$model")
    echo "[OK] CHAT_MODEL '$model' validated as $quant_type"
    return 0
}

# Validate tool model - must be in allowlist
validate_tool_model() {
    local model="$1"
    if [[ -z "$model" ]]; then
        echo "[ERROR] TOOL_MODEL is required but not set" >&2
        return 1
    fi
    
    for allowed in "${ALLOWED_TOOL_MODELS[@]}"; do
        if [[ "$model" == "$allowed" ]]; then
            echo "[OK] TOOL_MODEL '$model' is in allowlist"
            return 0
        fi
    done
    
    echo "[ERROR] TOOL_MODEL '$model' is not in the allowed list" >&2
    echo "[ERROR] See src/config/models.py for allowed tool models" >&2
    return 1
}

# Validate models based on deploy mode
validate_models_for_deploy() {
    local deploy_mode="$1"
    local chat_model="$2"
    local tool_model="$3"
    local errors=0
    
    case "$deploy_mode" in
        chat)
            validate_chat_model "$chat_model" || ((errors++))
            ;;
        tool)
            validate_tool_model "$tool_model" || ((errors++))
            ;;
        both)
            validate_chat_model "$chat_model" || ((errors++))
            validate_tool_model "$tool_model" || ((errors++))
            ;;
        *)
            echo "[ERROR] Invalid DEPLOY_MODELS: '$deploy_mode'. Must be chat|tool|both" >&2
            ((errors++))
            ;;
    esac
    
    return $errors
}

