#!/usr/bin/env python3
"""Shared utilities for Docker build-time downloads.

This module provides common functionality used by all download scripts,
including HuggingFace token handling and snapshot download helpers.
"""

import os
import sys


def get_hf_token() -> str | None:
    """Get HuggingFace token from environment or mounted secret.
    
    Priority:
        1. HF_TOKEN environment variable
        2. HUGGINGFACE_HUB_TOKEN environment variable
        3. /run/secrets/hf_token mounted secret (Docker BuildKit)
    
    Returns:
        Token string if found, None otherwise.
    """
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN") or None
    if token:
        return token
    
    secret_path = "/run/secrets/hf_token"
    if os.path.isfile(secret_path):
        with open(secret_path) as f:
            token = f.read().strip() or None
    
    return token


def download_snapshot(
    repo_id: str,
    target_dir: str,
    token: str | None = None,
    allow_patterns: list[str] | None = None,
    ignore_patterns: list[str] | None = None,
    log_prefix: str = "[build]",
) -> str:
    """Download files from HuggingFace repository.
    
    Args:
        repo_id: HuggingFace repository ID (e.g., "owner/repo")
        target_dir: Local directory to store downloaded files
        token: Optional HuggingFace token for private repos
        allow_patterns: Optional list of patterns to include
        ignore_patterns: Optional list of patterns to exclude
        log_prefix: Prefix for log messages
        
    Returns:
        Path to downloaded directory
        
    Raises:
        SystemExit: If download fails
    """
    from huggingface_hub import snapshot_download

    print(f"{log_prefix} Downloading from {repo_id}...")
    print(f"{log_prefix}   Target: {target_dir}")
    
    os.makedirs(target_dir, exist_ok=True)
    
    kwargs = {
        "repo_id": repo_id,
        "local_dir": target_dir,
        "token": token,
    }
    
    if allow_patterns:
        kwargs["allow_patterns"] = allow_patterns
        print(f"{log_prefix}   Allow patterns: {allow_patterns}")
    
    if ignore_patterns:
        kwargs["ignore_patterns"] = ignore_patterns
        print(f"{log_prefix}   Ignore patterns: {ignore_patterns}")
    
    try:
        local_path = snapshot_download(**kwargs)
        return local_path
    except Exception as e:
        print(f"{log_prefix} ERROR: Download failed: {e}", file=sys.stderr)
        sys.exit(1)


def verify_files_exist(
    target_dir: str,
    required_patterns: list[str] | None = None,
    file_extension: str | None = None,
    log_prefix: str = "[build]",
) -> list[str]:
    """Verify downloaded files exist and return their names.
    
    Args:
        target_dir: Directory to check
        required_patterns: Optional patterns that must match at least one file
        file_extension: Optional extension to filter (e.g., ".engine")
        log_prefix: Prefix for log messages
        
    Returns:
        List of matching file names
    """
    if not os.path.isdir(target_dir):
        print(f"{log_prefix} ERROR: Directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)
    
    files = os.listdir(target_dir)
    
    if file_extension:
        files = [f for f in files if f.endswith(file_extension)]
    
    if not files:
        ext_msg = f" with extension {file_extension}" if file_extension else ""
        print(f"{log_prefix} ERROR: No files found{ext_msg} in {target_dir}", file=sys.stderr)
        sys.exit(1)
    
    return files


def log_success(message: str, log_prefix: str = "[build]") -> None:
    """Log a success message."""
    print(f"{log_prefix} ✓ {message}")


def log_skip(message: str, log_prefix: str = "[build]") -> None:
    """Log a skip message."""
    print(f"{log_prefix} {message}")

