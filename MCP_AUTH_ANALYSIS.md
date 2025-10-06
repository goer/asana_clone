# MCP Server Authentication - Best Practices Analysis

**Date:** 2025-10-06
**Based on:** MCP Python SDK & FastAPI-MCP Documentation

---

## Executive Summary

After analyzing both the MCP Python SDK and FastAPI-MCP documentation, I've identified **the fundamental issue** with our current MCP implementation and the **correct approach** to authentication.

### The Core Problem

**Our current MCP server has a critical authentication design flaw:**

1. ✅ **MCP Protocol Layer** - Protected with API Key (`X-API-Key` header) - CORRECT
2. ❌ **Individual Tool Operations** - Require JWT Bearer tokens from app login - INCORRECT for MCP

This creates an **impossible workflow** for MCP clients because:
- MCP tools need to pass JWT tokens dynamically per request
- Static MCP HTTP client configuration only supports fixed headers
- Tools like `create_workspace` fail with 403 even after successful `register/login`

---

## How MCP Authentication Should Work

### According to MCP Python SDK Documentation

From `docs/modelcontextprotocol-python-sdk.txt`:

```python
# MCP servers act as Resource Servers (RS) that validate tokens
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

class SimpleTokenVerifier(TokenVerifier):
    """Verify tokens issued by Authorization Server"""
    async def verify_token(self, token: str) -> AccessToken | None:
        # Validate the token against your auth system
        pass

# Create FastMCP instance as a Resource Server
mcp = FastMCP(
    "Weather Service",
    token_verifier=SimpleTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl("https://auth.example.com"),
        resource_server_url=AnyHttpUrl("http://localhost:3001"),
        required_scopes=["user"],
    ),
)
```

### According to FastAPI-MCP Documentation

From `docs/tadata-org-fastapi_mcp.txt`:

#### **Option 1: API Key Pass-Through (Simple)**

```python
from fastapi import Depends
from fastapi_mcp import FastApiMCP, AuthConfig

# Just verify API key at MCP protocol level
mcp = FastApiMCP(
    app,
    name="Protected MCP",
    auth_config=AuthConfig(
        dependencies=[Depends(verify_api_key)],  # Check API key
    ),
)
mcp.mount_http()
```

**Key Point:** Individual FastAPI endpoints can still have their own auth, but MCP passes through headers automatically.

#### **Option 2: OAuth 2.0 Flow (Standard MCP)**

```python
from fastapi import Depends
from fastapi_mcp import FastApiMCP, AuthConfig

mcp = FastApiMCP(
    app,
    name="MCP With OAuth",
    auth_config=AuthConfig(
        issuer="https://auth.example.com/",
        authorize_url="https://auth.example.com/authorize",
        oauth_metadata_url="https://auth.example.com/.well-known/oauth-authorization-server",
        audience="my-audience",
        client_id="my-client-id",
        client_secret="my-client-secret",
        dependencies=[Depends(verify_auth)],
        setup_proxies=True,  # Makes OAuth provider compatible with MCP
    ),
)
mcp.mount_http()
```

---

## Our Current Implementation Issues

### What We Did (INCORRECT)

```python
# app/mcp_server.py - PROBLEM

# Every endpoint requires JWT authentication
@router.post("/workspaces")
def create_workspace(
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ❌ JWT required
) -> WorkspaceResponse:
    pass
```

**Why this doesn't work:**
1. MCP client connects with API key → ✅ Works
2. MCP client calls `mcp_register` → ✅ Gets JWT token
3. MCP client calls `mcp_create_workspace` → ❌ **FAILS with 403**
   - Tool call doesn't include the JWT token from step 2
   - MCP HTTP client only sends static headers (`X-API-Key`)
   - No way to pass dynamic Bearer token per tool call

### What We Should Do (CORRECT)

**Two Recommended Approaches:**

#### **Approach A: Single-Tier Auth (API Key Only)**

```python
# Simple: Only verify API key at MCP level, no per-endpoint auth

# app/mcp_server.py
mcp = FastApiMCP(
    mcp_app,  # Simplified app without auth dependencies
    name="Asana Clone MCP",
    auth_config=AuthConfig(
        dependencies=[Depends(verify_api_key)],  # Only this
    ),
)
mcp.mount_http(app)

# Endpoints DON'T require auth
@router.post("/workspaces")
def create_workspace(
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db)
    # No current_user dependency!
) -> WorkspaceResponse:
    # API key already verified by MCP layer
    # Create workspace without user context
    pass
```

**Pros:**
- ✅ Simple implementation
- ✅ Works with all MCP clients
- ✅ No authentication flow complexity

**Cons:**
- ❌ No per-user permissions
- ❌ All API key holders have full access
- ❌ Can't track which user created what

#### **Approach B: OAuth 2.0 Flow (Standard MCP)**

```python
# app/mcp_server.py - Full OAuth implementation

mcp = FastApiMCP(
    mcp_app,
    name="Asana Clone MCP",
    auth_config=AuthConfig(
        # OAuth configuration
        issuer="http://localhost:8000",
        authorize_url="http://localhost:8000/auth/authorize",
        oauth_metadata_url="http://localhost:8000/.well-known/oauth-authorization-server",

        # App credentials
        client_id="asana-mcp-client",
        client_secret="asana-mcp-secret",
        audience="asana-api",
        default_scope="user",

        # Verify tokens
        dependencies=[Depends(verify_oauth_token)],
        setup_proxies=True,
    ),
)
mcp.mount_http(app)
```

Then implement OAuth server endpoints:
- `/auth/authorize` - Authorization endpoint
- `/auth/token` - Token exchange endpoint
- `/.well-known/oauth-authorization-server` - OAuth metadata

**Pros:**
- ✅ Standard MCP authentication
- ✅ Per-user permissions possible
- ✅ Secure token-based auth
- ✅ Follows MCP specification

**Cons:**
- ❌ Complex implementation
- ❌ Requires OAuth server setup
- ❌ Most MCP clients need `mcp-remote` bridge

---

## Recommended Solution for Asana Clone

### **Approach: API Key + Context Injection**

A hybrid approach that works well for internal/development use:

```python
# app/mcp_auth.py - Enhanced version

from fastapi import Header, HTTPException, Depends
from fastapi.security import APIKeyHeader

MCP_API_KEY = os.getenv("MCP_API_KEY", "asana-mcp-secret-key-2025")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(x_api_key: str = Depends(api_key_header)):
    """Verify API key for MCP protocol access"""
    if x_api_key != MCP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

async def get_mcp_user_context(
    x_mcp_user: str = Header(None),  # Optional user context
    db: Session = Depends(get_db)
):
    """Get user context from MCP request headers"""
    if x_mcp_user:
        user = db.query(User).filter(User.email == x_mcp_user).first()
        if user:
            return user

    # Return system/default user for operations
    return None  # Or create a system user


# app/mcp_server.py - Updated endpoints

@router.post("/workspaces")
def create_workspace(
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_mcp_user_context)  # Optional context
) -> WorkspaceResponse:
    """Create workspace - uses API key auth + optional user context"""
    owner_id = user.id if user else 1  # System user as fallback

    workspace = Workspace(name=payload.name, owner_id=owner_id)
    db.add(workspace)
    db.commit()
    return WorkspaceResponse.from_orm(workspace)
```

**MCP Configuration:**

```json
{
  "mcpServers": {
    "asana": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "admin@example.com"  // Optional user context
      }
    }
  }
}
```

**Benefits:**
- ✅ Simple API key authentication
- ✅ Optional user context for permissions
- ✅ Works with all MCP clients
- ✅ No complex OAuth setup needed
- ✅ Good for development/internal use

---

## Implementation Steps

### Step 1: Remove JWT Dependencies from MCP Endpoints

```bash
# Remove Depends(get_current_user) from all MCP endpoint functions
```

### Step 2: Update MCP Auth Configuration

```python
# app/main.py

mcp = FastApiMCP(
    mcp_app,
    name="Asana Clone MCP",
    auth_config=AuthConfig(
        dependencies=[Depends(verify_api_key)],
    ),
)
mcp.mount_http(app, path="/mcp")
```

### Step 3: Add Optional User Context

```python
# app/mcp_auth.py - Add get_mcp_user_context()
# app/mcp_server.py - Use Depends(get_mcp_user_context) instead of get_current_user
```

### Step 4: Test MCP Tools

```python
# All tools should now work:
mcp__asana__mcp_register()        # Creates user (no auth needed)
mcp__asana__mcp_login()           # Returns JWT (not used by MCP)
mcp__asana__mcp_create_workspace() # ✅ NOW WORKS (API key sufficient)
mcp__asana__mcp_list_workspaces()  # ✅ NOW WORKS
```

---

## Key Takeaways

1. **MCP ≠ REST API Authentication**
   - MCP tools are NOT like REST API endpoints
   - They use protocol-level authentication (API key or OAuth)
   - Individual tool calls don't carry per-request auth tokens

2. **FastAPI-MCP Handles Auth Differently**
   - Use `AuthConfig` for MCP protocol authentication
   - Don't use FastAPI `Depends(get_current_user)` in MCP endpoints
   - Headers are passed through automatically

3. **Choose Auth Based on Use Case**
   - **Development/Internal:** API Key + Optional User Context
   - **Production/External:** OAuth 2.0 Flow
   - **Maximum Security:** Separate MCP app with limited scope

4. **Our Previous Approach Was Wrong**
   - Mixing FastAPI JWT auth with MCP protocol doesn't work
   - MCP clients can't dynamically inject Bearer tokens
   - Need to authenticate at protocol level, not endpoint level

---

## References

- [MCP Python SDK - Authentication](https://github.com/modelcontextprotocol/python-sdk)
- [FastAPI-MCP - Authentication Guide](https://fastapi-mcp.tadata.com/advanced/auth)
- [MCP Specification - Authorization](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization)
- [OAuth 2.1 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [Dynamic Client Registration RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591)

---

**Generated:** 2025-10-06
**Status:** ✅ READY FOR IMPLEMENTATION
