"""CLI argument-count constants.

Guards the minimum argument counts and flag indices for CLI entry points
in src.scripts. Prefixed by command name to prevent collisions.

Sections:
    Deploy: src.scripts.deploy CLI thresholds
    Package: src.scripts.validation.package CLI thresholds
    Parser: src.scripts.metadata.parser CLI thresholds
    Versions: src.scripts.metadata.versions CLI thresholds
"""

from __future__ import annotations

# =============================================================================
# Deploy CLI Constants
# =============================================================================

DEPLOY_ENGINE_LABEL_PARTS_MIN = 4  # Minimum path parts in engine label
DEPLOY_DOWNLOAD_ARGS_MIN = 4  # Minimum args for download subcommand

# =============================================================================
# Package Validation CLI Constants
# =============================================================================

PACKAGE_MIN_ARGS = 2  # Minimum args for package validation CLI

# =============================================================================
# Metadata Parser CLI Constants
# =============================================================================

PARSER_MIN_ARGS = 2  # Minimum args for parser CLI
PARSER_SM_ARCH_FLAG_INDEX = 2  # Index of --sm-arch flag in argv

# =============================================================================
# Metadata Versions CLI Constants
# =============================================================================

VERSIONS_MIN_ARGS = 2  # Minimum args for versions CLI


__all__ = [
    "DEPLOY_DOWNLOAD_ARGS_MIN",
    "DEPLOY_ENGINE_LABEL_PARTS_MIN",
    "PACKAGE_MIN_ARGS",
    "PARSER_MIN_ARGS",
    "PARSER_SM_ARCH_FLAG_INDEX",
    "VERSIONS_MIN_ARGS",
]
