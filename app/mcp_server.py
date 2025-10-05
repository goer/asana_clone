"""
Separate MCP server with simplified schemas to avoid recursion issues.

This module creates a standalone FastAPI application specifically for MCP integration.
It exposes simplified versions of the Asana Clone API endpoints without the deep
nesting that causes recursion in fastapi-mcp's schema resolver.
"""
import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.deps import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.db.session import get_db

logger = logging.getLogger(__name__)

# Simplified schemas without deep nesting
class UserRegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    token: str
    user_id: int
    email: str
    name: str

class SimpleWorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_id: int

class WorkspaceCreateRequest(BaseModel):
    name: str

# Create a separate FastAPI app for MCP
mcp_app = FastAPI(
    title="Asana Clone MCP API",
    description="Simplified API for Model Context Protocol integration",
    version="1.0.0",
)

@mcp_app.post("/mcp/auth/register", response_model=TokenResponse, operation_id="mcp_register")
def mcp_register(request: UserRegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user (MCP version)."""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    hashed_password = get_password_hash(request.password)
    user = User(email=request.email, name=request.name, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    token = create_access_token(subject=user.id)

    return TokenResponse(
        token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )

@mcp_app.post("/mcp/auth/login", response_model=TokenResponse, operation_id="mcp_login")
def mcp_login(request: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Login user (MCP version)."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=user.id)

    return TokenResponse(
        token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )

@mcp_app.post("/mcp/workspaces", response_model=SimpleWorkspaceResponse, operation_id="mcp_create_workspace")
def mcp_create_workspace(
    request: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SimpleWorkspaceResponse:
    """Create a workspace (MCP version with simplified response)."""
    workspace = Workspace(name=request.name, owner_id=current_user.id)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    return SimpleWorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
    )

@mcp_app.get("/mcp/health", operation_id="mcp_health")
def mcp_health() -> dict[str, str]:
    """Health check for MCP API."""
    return {"status": "ok", "api": "mcp"}


def create_mcp_server() -> FastAPI | None:
    """
    Create and configure MCP server with transports.

    Returns None if MCP setup fails (e.g., due to recursion errors).
    """
    try:
        from fastapi_mcp import FastApiMCP

        mcp = FastApiMCP(
            mcp_app,
            name="Asana Clone MCP",
            description="Model Context Protocol interface for Asana Clone API",
            describe_full_response_schema=False,
            describe_all_responses=False,
        )

        # Mount transports
        mcp.mount_http()
        mcp.mount_sse()

        logger.info("✓ MCP server created successfully with HTTP and SSE transports")
        return mcp_app

    except RecursionError as e:
        logger.error(f"✗ RecursionError while setting up MCP: {e}")
        return None
    except Exception as e:
        logger.error(f"✗ Failed to setup MCP: {type(e).__name__}: {e}")
        return None
