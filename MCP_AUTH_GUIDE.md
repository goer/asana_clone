# MCP Authentication Guide - Asana Clone

**Date:** 2025-10-06
**Status:** ✅ **IMPLEMENTED - API Key + Optional User Context**

---

## Executive Summary

The Asana Clone API now has **dual authentication architecture**:

1. **Main REST API** (`/workspaces`, `/tasks`, etc.) - Uses JWT Bearer tokens (standard REST auth)
2. **MCP Tools** (`mcp__asana__*`) - Uses API Key + Optional User Context (MCP protocol auth)

This follows FastAPI-MCP best practices where MCP tools authenticate at the protocol level, not at individual endpoint level.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Main FastAPI App                         │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ REST API Routers (app/routers/*.py)                   │ │
│  │ - /auth/register, /auth/login                         │ │
│  │ - /workspaces, /projects, /tasks, etc.                │ │
│  │ - Authentication: JWT Bearer Token (required)          │ │
│  │ - Uses: Depends(get_current_user)                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ MCP Protocol Endpoint (/mcp)                          │ │
│  │                                                       │ │
│  │   Wraps: mcp_app (Simplified FastAPI app)            │ │
│  │   ┌──────────────────────────────────────────┐       │ │
│  │   │ MCP Simplified Endpoints                  │       │ │
│  │   │ - POST /auth/register, /auth/login       │       │ │
│  │   │ - POST /workspaces, GET /workspaces      │       │ │
│  │   │ - POST /tasks, GET /tasks, etc.          │       │ │
│  │   │ - Authentication: API Key (protocol)     │       │ │
│  │   │ - Optional: User Context (X-Mcp-User)    │       │ │
│  │   │ - Uses: Depends(get_mcp_user_context)    │       │ │
│  │   └──────────────────────────────────────────┘       │ │
│  │                                                       │ │
│  │   Access: MCP JSON-RPC 2.0 protocol only             │ │
│  │   Headers:                                            │ │
│  │     - X-API-Key: asana-mcp-secret-key-2025          │ │
│  │     - X-Mcp-User: admin@example.com (optional)      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## User Context Behavior

### With User Context (X-Mcp-User: admin@example.com)

- User lookup: db.query(User).filter(User.email == "admin@example.com")
- If found: Operations use user.id for ownership/permissions
- If not found: Falls back to system user (ID=1)

### Without User Context

- No user lookup
- Operations use system user (ID=1) for ownership
- List operations may return all resources (no user filtering)

---

## How to Use MCP Tools

### Via Claude Code (Recommended)

**Step 1: Add MCP Server Configuration**

Create/edit `~/.config/claude-code/mcp.json`:

```json
{
  "mcpServers": {
    "asana-clone": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "admin@example.com"
      }
    }
  }
}
```

**Step 2: Restart Claude Code**

**Step 3: Use MCP Tools**

```
> Create a new workspace called "Q1 2025 Planning"

Claude will call:
mcp__asana-clone__mcp_create_workspace(name="Q1 2025 Planning")
```

---

## MCP Tools Available (43 Operations)

- Authentication (2): register, login
- Workspaces (5): list, create, get, update, delete
- Projects (5): list, create, get, update, delete
- Tasks (5): list, create, get, update, delete
- Sections (4): list, create, update, delete
- Comments (4): list, create, update, delete
- Tags (6): list, create, update, delete, add to task, remove from task
- Teams (4): list, create, add member, remove member
- Attachments (3): list, create, delete
- Custom Fields (5): list, create, delete, set value, clear value

See REPORT.md for complete details.

---

## Implementation Files

| File | Purpose |
|------|---------|
| `app/mcp_auth.py` | verify_api_key(), get_mcp_user_context() |
| `app/mcp_server.py` | 43 endpoint implementations with optional user context |
| `app/main.py` | MCP server mounting with HTTP transport |

---

**Last Updated:** 2025-10-06
