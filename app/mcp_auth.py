"""
MCP Authentication using API Key.

This module provides API key authentication for the MCP server and optional user context.
Following FastAPI-MCP best practices, MCP tools authenticate at the protocol level (API key),
not at the individual endpoint level (JWT tokens).
"""
import os
from typing import Optional
from fastapi import HTTPException, Security, status, Header, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User

# API key header name
API_KEY_NAME = "X-API-Key"

# Get API key from environment variable
# In production, this should be stored securely (e.g., in secrets manager)
MCP_API_KEY = os.getenv("MCP_API_KEY", "asana-mcp-secret-key-2025")

# Create the API key header security scheme
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key from the request header.

    This is the primary authentication for the MCP protocol layer.
    All MCP tool calls must include a valid API key.

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


async def get_mcp_user_context(
    x_mcp_user: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get optional user context from MCP request headers.

    This allows MCP clients to specify which user context to use for operations
    by including an X-Mcp-User header with the user's email.

    If no user is specified or the user doesn't exist, returns None.
    The calling code can then use a default/system user or handle the case appropriately.

    Example MCP client configuration:
    {
      "headers": {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "admin@example.com"  // Optional user context
      }
    }

    Args:
        x_mcp_user: Optional email from X-Mcp-User header
        db: Database session

    Returns:
        User object if found, None otherwise
    """
    if not x_mcp_user:
        return None

    # Try to find user by email
    user = db.query(User).filter(User.email == x_mcp_user).first()
    return user
