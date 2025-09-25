"""Authentication utilities for API key validation."""

import logging
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyQuery, APIKeyHeader
from fastapi import WebSocket

from .config import API_KEY

logger = logging.getLogger(__name__)

# API Key can be provided via query parameter or header
api_key_query = APIKeyQuery(name="api_key", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def validate_api_key(provided_key: str) -> bool:
    """Validate provided API key against configured key.
    
    Args:
        provided_key: The API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    return provided_key == API_KEY


async def get_api_key(
    api_key_query: Optional[str] = Security(api_key_query),
    api_key_header: Optional[str] = Security(api_key_header),
) -> str:
    """FastAPI dependency to extract and validate API key from request.
    
    Args:
        api_key_query: API key from query parameter
        api_key_header: API key from X-API-Key header
        
    Returns:
        Valid API key string
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Try header first, then query parameter
    provided_key = api_key_header or api_key_query
    
    if not provided_key:
        logger.warning("API key missing from request")
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via 'X-API-Key' header or 'api_key' query parameter."
        )
    
    if not validate_api_key(provided_key):
        logger.warning(f"Invalid API key provided: {provided_key[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key."
        )
    
    return provided_key


def extract_websocket_api_key(websocket: WebSocket) -> Optional[str]:
    """Extract API key from WebSocket connection.
    
    Args:
        websocket: WebSocket connection
        
    Returns:
        API key if found, None otherwise
    """
    # Try query parameters first
    query_params = dict(websocket.query_params)
    api_key = query_params.get("api_key")
    
    if api_key:
        return api_key
    
    # Try headers
    headers = dict(websocket.headers)
    api_key = headers.get("x-api-key") or headers.get("X-API-Key")
    
    return api_key


async def authenticate_websocket(websocket: WebSocket) -> bool:
    """Authenticate WebSocket connection using API key.
    
    Args:
        websocket: WebSocket connection to authenticate
        
    Returns:
        True if authenticated, False otherwise
    """
    provided_key = extract_websocket_api_key(websocket)
    
    if not provided_key:
        logger.warning("WebSocket connection missing API key")
        return False
    
    if not validate_api_key(provided_key):
        logger.warning(f"WebSocket connection with invalid API key: {provided_key[:8]}...")
        return False
    
    logger.info("WebSocket connection authenticated successfully")
    return True
