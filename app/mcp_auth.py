"""
MCP Authentication using API Key.

This module provides simple API key authentication for the MCP server.
"""
import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# API key header name
API_KEY_NAME = "X-API-Key"

# Get API key from environment variable
# In production, this should be stored securely (e.g., in secrets manager)
MCP_API_KEY = os.getenv("MCP_API_KEY", "your-secret-api-key-change-this")

# Create the API key header security scheme
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key from the request header.

    Args:
        api_key: The API key from the X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If the API key is invalid
    """
    if api_key != MCP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key
