# MCP API Key Authentication Guide

## Overview

The Asana Clone MCP server is protected with API key authentication to ensure secure access to all MCP tools and endpoints.

## Exposed API Endpoints

The MCP server exposes **25 complete CRUD endpoints** across all major resources:

### Authentication (2 endpoints)
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token

### Workspaces (5 endpoints)
- `GET /workspaces` - List all workspaces
- `POST /workspaces` - Create a workspace
- `GET /workspaces/{workspace_id}` - Get workspace details
- `PATCH /workspaces/{workspace_id}` - Update workspace
- `DELETE /workspaces/{workspace_id}` - Delete workspace

### Projects (5 endpoints)
- `GET /projects?workspace_id={id}` - List projects in workspace
- `POST /projects` - Create a project
- `GET /projects/{project_id}` - Get project details
- `PATCH /projects/{project_id}` - Update project
- `DELETE /projects/{project_id}` - Delete project

### Tasks (5 endpoints)
- `GET /tasks?workspace_id={id}` - List tasks (with filters)
- `POST /tasks` - Create a task
- `GET /tasks/{task_id}` - Get task details
- `PATCH /tasks/{task_id}` - Update task
- `DELETE /tasks/{task_id}` - Delete task

### Sections (4 endpoints)
- `GET /sections?project_id={id}` - List sections in project
- `POST /sections` - Create a section
- `PATCH /sections/{section_id}` - Update section
- `DELETE /sections/{section_id}` - Delete section

### Comments (4 endpoints)
- `GET /tasks/{task_id}/comments` - List comments on task
- `POST /tasks/{task_id}/comments` - Create a comment
- `PATCH /comments/{comment_id}` - Update comment
- `DELETE /comments/{comment_id}` - Delete comment

All endpoints use **simplified schemas** (no nested objects) to avoid recursion issues with fastapi-mcp's OpenAPI schema processor.

## Configuration

### Server Side

1. **Set the API Key** in `.env`:
   ```bash
   MCP_API_KEY=your-secret-api-key-here
   ```

2. **Restart the server** after changing the API key:
   ```bash
   docker-compose restart api
   # or
   docker-compose up -d --force-recreate api
   ```

### Client Side

All requests to the MCP server must include the API key in the `X-API-Key` header.

## Testing with curl

### 1. Initialize MCP Session (with API key)

```bash
curl -X POST http://localhost:8000/mcp-api/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-API-Key: asana-mcp-secret-key-2025" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0"
      }
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "experimental": {},
      "tools": {
        "listChanged": false
      }
    },
    "serverInfo": {
      "name": "Asana Clone MCP",
      "version": "Model Context Protocol interface for Asana Clone API"
    }
  }
}
```

The response will include an `mcp-session-id` header that must be used in subsequent requests.

### 2. Direct API Endpoints (also require API key)

All the simplified API endpoints also require the API key:

```bash
# Register a new user
curl -X POST http://localhost:8000/mcp-api/mcp/auth/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: asana-mcp-secret-key-2025" \
  -d '{
    "email": "user@example.com",
    "name": "Test User",
    "password": "securepass123"
  }'

# Login
curl -X POST http://localhost:8000/mcp-api/mcp/auth/login \
  -H "Content-Type: application/json" \
  -H "X-API-Key: asana-mcp-secret-key-2025" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'

# Create workspace (requires auth token from login)
curl -X POST http://localhost:8000/mcp-api/mcp/workspaces \
  -H "Content-Type: application/json" \
  -H "X-API-Key: asana-mcp-secret-key-2025" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "My Workspace"
  }'
```

## Using with Claude Code MCP Tools

To configure Claude Code to use the API key with MCP tools, you need to set up the MCP server configuration with the custom header.

### Option 1: Environment Variable (Recommended)

In your MCP server configuration (typically in Claude Desktop config):

```json
{
  "mcpServers": {
    "asana-clone": {
      "url": "http://localhost:8000/mcp-api/mcp",
      "transport": "http",
      "headers": {
        "X-API-Key": "${ASANA_MCP_API_KEY}"
      }
    }
  }
}
```

Then set the environment variable:
```bash
export ASANA_MCP_API_KEY=asana-mcp-secret-key-2025
```

### Option 2: Direct Configuration

```json
{
  "mcpServers": {
    "asana-clone": {
      "url": "http://localhost:8000/mcp-api/mcp",
      "transport": "http",
      "headers": {
        "X-API-Key": "asana-mcp-secret-key-2025"
      }
    }
  }
}
```

**⚠️ Security Warning:** Never commit API keys directly in configuration files. Always use environment variables in production.

## Error Responses

### Missing API Key
```json
{
  "detail": "Not authenticated"
}
```

### Invalid API Key
```json
{
  "detail": "Invalid API Key"
}
```

## Security Best Practices

1. **Use strong API keys** - Generate cryptographically secure random strings
2. **Rotate keys regularly** - Change API keys periodically
3. **Use environment variables** - Never hardcode keys in source code
4. **Use HTTPS in production** - Always use TLS encryption for API communication
5. **Implement rate limiting** - Add rate limiting to prevent abuse
6. **Monitor access** - Log and monitor API key usage
7. **Use different keys per environment** - Development, staging, and production should have different keys

## Generating Secure API Keys

```python
import secrets
import string

def generate_api_key(length=32):
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Example:
print(generate_api_key())
# Output: asana-mcp-7kL9mP4nQ2wX8vB6zR3yT5uH1jG0fD
```

Or using command line:
```bash
# Linux/Mac
openssl rand -base64 32

# Python one-liner
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Implementation Details

The API key authentication is implemented using:

- **FastAPI Security**: `APIKeyHeader` from `fastapi.security`
- **fastapi-mcp**: `AuthConfig` with dependencies
- **Middleware**: Applied to all MCP protocol endpoints

See:
- `app/mcp_auth.py` - Authentication implementation
- `app/mcp_server.py` - MCP server configuration with auth
