#!/usr/bin/env bash
# =============================================================================
# String Utilities
# =============================================================================
# Common string manipulation functions shared across shell scripts.
# Source this file to avoid duplicating basic string operations.

# Convert a string to lowercase.
# Works on both Bash 4+ (using ${var,,}) and older Bash (using tr).
# Usage: str_to_lower "HELLO" -> "hello"
str_to_lower() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    echo ""
    return
  fi
  if [[ -n "${BASH_VERSION:-}" && "${BASH_VERSION%%.*}" -ge 4 ]]; then
    echo "${value,,}"
  else
    echo "${value}" | tr '[:upper:]' '[:lower:]'
  fi
}

# Convert a string to uppercase.
# Works on both Bash 4+ (using ${var^^}) and older Bash (using tr).
# Usage: str_to_upper "hello" -> "HELLO"
str_to_upper() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    echo ""
    return
  fi
  if [[ -n "${BASH_VERSION:-}" && "${BASH_VERSION%%.*}" -ge 4 ]]; then
    echo "${value^^}"
  else
    echo "${value}" | tr '[:lower:]' '[:upper:]'
  fi
}

# Trim leading and trailing whitespace from a string.
# Usage: str_trim "  hello world  " -> "hello world"
str_trim() {
  local value="${1:-}"
  # Remove leading whitespace
  value="${value#"${value%%[![:space:]]*}"}"
  # Remove trailing whitespace
  value="${value%"${value##*[![:space:]]}"}"
  echo "${value}"
}

# Check if a string contains a substring.
# Usage: str_contains "hello world" "world" && echo "found"
str_contains() {
  local haystack="${1:-}"
  local needle="${2:-}"
  [[ "${haystack}" == *"${needle}"* ]]
}

# Check if a string contains any of the provided substrings.
# Usage: str_contains_any "hello world" "foo" "world" "bar" && echo "found"
str_contains_any() {
  local haystack="${1:-}"
  shift
  local needle
  for needle in "$@"; do
    if str_contains "${haystack}" "${needle}"; then
      return 0
    fi
  done
  return 1
}

