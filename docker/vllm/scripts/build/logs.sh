#!/usr/bin/env bash

# Logging utilities for build scripts

log_info() {
  echo "$*"
}

log_warn() {
  echo "$*" >&2
}

log_error() {
  echo "$*" >&2
}

log_success() {
  echo "$*"
}

