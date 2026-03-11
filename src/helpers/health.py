"""Health endpoint access control helpers."""

from __future__ import annotations

from fastapi import Request, HTTPException
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network

HealthNetwork = IPv4Network | IPv6Network


def parse_health_allowed_cidrs(raw: str) -> tuple[HealthNetwork, ...]:
    """Parse the configured health CIDR allowlist."""
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise ValueError("HEALTH_ALLOWED_CIDRS must contain at least one CIDR")
    return tuple(ip_network(part, strict=False) for part in parts)


def is_health_client_allowed(
    client_host: str | None,
    *,
    allowed_cidrs: tuple[HealthNetwork, ...],
) -> bool:
    """Return True when the client host is inside the health allowlist."""
    if not client_host:
        return False
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False
    return any(client_ip in network for network in allowed_cidrs)


def ensure_internal_health_request(
    request: Request,
    *,
    allowed_cidrs: tuple[HealthNetwork, ...],
) -> None:
    """Hide the health endpoint from non-allowlisted clients."""
    client = request.client
    client_host = client.host if client else None
    if not is_health_client_allowed(client_host, allowed_cidrs=allowed_cidrs):
        raise HTTPException(status_code=404)


__all__ = [
    "HealthNetwork",
    "parse_health_allowed_cidrs",
    "is_health_client_allowed",
    "ensure_internal_health_request",
]
