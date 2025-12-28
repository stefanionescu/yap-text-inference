#!/usr/bin/env bash

# Stop script environment defaults.

stop_init_flags() {
  export HARD_RESET="${HARD_RESET:-0}"
  export NUKE_ALL="${NUKE_ALL:-1}"
}

