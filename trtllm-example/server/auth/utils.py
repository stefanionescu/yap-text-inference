import logging
import secrets

from fastapi import WebSocket
from huggingface_hub import login

from server.config import settings

logger = logging.getLogger(__name__)


def ensure_hf_login():
    tok = settings.hf_token
    if not tok:
        raise RuntimeError("HF_TOKEN not set")
    login(token=tok, add_to_git_credential=False)


def extract_api_key_from_ws(ws: WebSocket) -> str | None:
    """
    Extract API key from WebSocket headers.
    Requires either:
      - Authorization: Bearer <token>
      - X-API-Key: <token>
    """
    try:
        headers = getattr(ws, "headers", None)
        if not headers:
            return None
        auth_header = headers.get("authorization")
        if auth_header:
            scheme, _, token = str(auth_header).strip().partition(" ")
            scheme = scheme.lower()
            token = token.strip()
            if scheme in {"bearer", "token"} and token:
                return token
            if scheme == "" and auth_header:
                return str(auth_header).strip()
        keyed = headers.get("x-api-key") or headers.get("x_api_key")
        if keyed:
            return str(keyed).strip()
    except Exception:
        return None
    return None


def is_api_key_authorized(provided_key: str | None) -> bool:
    expected = settings.api_key or ""
    got = (provided_key or "").strip()
    return secrets.compare_digest(got, expected)
