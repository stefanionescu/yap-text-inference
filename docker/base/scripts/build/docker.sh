#!/usr/bin/env bash

require_docker() {
  if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
  fi
}

ensure_docker_login() {
  if docker info 2>/dev/null | grep -q "Username:"; then
    log_info "Docker login detected."
    return
  fi
  if [ -n "${DOCKER_PASSWORD:-}" ]; then
    echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin && return
  fi
  if [ -n "${DOCKER_TOKEN:-}" ]; then
    echo "${DOCKER_TOKEN}" | docker login -u "${DOCKER_USERNAME}" --password-stdin && return
  fi
  log_warn "Not logged in to Docker Hub and no DOCKER_PASSWORD/DOCKER_TOKEN set; push may fail."
}


