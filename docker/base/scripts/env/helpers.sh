#!/usr/bin/env bash

# Helper utilities for env configuration

norm_lower() {
  echo "$1" | tr '[:upper:]' '[:lower:]'
}

is_gptq_name() {
  case "$(norm_lower "$1")" in
    *gptq*) return 0 ;;
    *) return 1 ;;
  esac
}

file_exists() { [ -e "$1" ]; }


