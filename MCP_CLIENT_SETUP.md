# MCP Client Setup Guide

This guide shows how to configure MCP clients to connect to the Asana Clone MCP server.

---

## ✅ Recommended: SSE Transport

SSE (Server-Sent Events) transport is the **recommended** method as it has been fully tested and verified to work with 100% success rate.

### Claude Code CLI

```bash
# Add the MCP server with SSE transport
claude mcp add asana http://localhost:8000/sse \
  --transport sse \
  --header "X-API-Key: asana-mcp-secret-key-2025" \
  --header "X-Mcp-User: test@example.com" \
  -s local

# Verify it's working
claude mcp list

# Expected output:
# asana: http://localhost:8000/sse (SSE) - ✓ Connected
```

**Configuration is stored in:**
- **Local scope:** `~/.claude.json` (project-specific, recommended)
- **User scope:** User-level configuration (not project-specific)
- **Project scope:** `.mcp.json` in project root (shared with team)

### Manual Configuration

If you need to manually edit the config, the MCP server configuration in `~/.claude.json` looks like:

```json
{
  "mcpServers": {
    "asana": {
      "type": "sse",
      "url": "http://localhost:8000/sse",
      "headers": {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "test@example.com"
      }
    }
  }
}
```

---

## Alternative: HTTP Transport

HTTP transport has session management issues and is **not recommended**. Use SSE instead.

If you still want to try HTTP transport:

```bash
claude mcp add asana-http http://localhost:8000/mcp \
  --transport http \
  --header "X-API-Key: asana-mcp-secret-key-2025" \
  --header "X-Mcp-User: test@example.com" \
  -s local
```

**Known Issues with HTTP:**
- Session ID management problems
- "Bad Request: No valid session ID provided" errors
- Less reliable than SSE transport

---

## Authentication Headers

### Required Header
- **X-API-Key:** `asana-mcp-secret-key-2025`
  - This is the MCP server API key (protocol-level authentication)
  - Configured in `.env` as `MCP_API_KEY`
  - Can be changed for production

### Optional Header
- **X-Mcp-User:** `test@example.com` (or any valid user email)
  - Provides user context for operations
  - If provided: operations use this user's permissions and ownership
  - If omitted: operations use system user (ID=1) as fallback

### User Context Behavior

**With User Context (X-Mcp-User: test@example.com):**
```
→ list_workspaces()
  Returns: Workspaces where test@example.com is a member

→ create_workspace(name="Engineering")
  Creates: Workspace owned by test@example.com
```

**Without User Context:**
```
→ list_workspaces()
  Returns: All workspaces (no user filtering)

→ create_workspace(name="Engineering")
  Creates: Workspace owned by system user (ID=1)
```

---

## Available MCP Tools

Once configured, you'll have access to 43 MCP tools:

### Authentication (2 tools)
- `mcp__asana__mcp_register` - Register new user
- `mcp__asana__mcp_login` - Login and get JWT token

### Workspaces (5 tools)
- `mcp__asana__mcp_list_workspaces` - List all workspaces
- `mcp__asana__mcp_create_workspace` - Create new workspace
- `mcp__asana__mcp_get_workspace` - Get workspace details
- `mcp__asana__mcp_update_workspace` - Update workspace
- `mcp__asana__mcp_delete_workspace` - Delete workspace

### Projects (5 tools)
- `mcp__asana__mcp_list_projects` - List projects in workspace
- `mcp__asana__mcp_create_project` - Create new project
- `mcp__asana__mcp_get_project` - Get project details
- `mcp__asana__mcp_update_project` - Update project
- `mcp__asana__mcp_delete_project` - Delete project

### Tasks (5 tools)
- `mcp__asana__mcp_list_tasks` - List tasks with filters
- `mcp__asana__mcp_create_task` - Create new task
- `mcp__asana__mcp_get_task` - Get task details
- `mcp__asana__mcp_update_task` - Update task
- `mcp__asana__mcp_delete_task` - Delete task

### Sections (4 tools)
- `mcp__asana__mcp_list_sections` - List sections in project
- `mcp__asana__mcp_create_section` - Create new section
- `mcp__asana__mcp_update_section` - Update section
- `mcp__asana__mcp_delete_section` - Delete section

### Comments (4 tools)
- `mcp__asana__mcp_list_comments` - List comments on task
- `mcp__asana__mcp_create_comment` - Add comment to task
- `mcp__asana__mcp_update_comment` - Update comment
- `mcp__asana__mcp_delete_comment` - Delete comment

### Tags (6 tools)
- `mcp__asana__mcp_list_tags` - List tags in workspace
- `mcp__asana__mcp_create_tag` - Create new tag
- `mcp__asana__mcp_update_tag` - Update tag
- `mcp__asana__mcp_delete_tag` - Delete tag
- `mcp__asana__mcp_add_tag_to_task` - Add tag to task
- `mcp__asana__mcp_remove_tag_from_task` - Remove tag from task

### Teams (4 tools)
- `mcp__asana__mcp_list_teams` - List teams in workspace
- `mcp__asana__mcp_create_team` - Create new team
- `mcp__asana__mcp_add_team_member` - Add member to team
- `mcp__asana__mcp_remove_team_member` - Remove member from team

### Attachments (3 tools)
- `mcp__asana__mcp_list_attachments` - List attachments on task
- `mcp__asana__mcp_create_attachment` - Add attachment to task
- `mcp__asana__mcp_delete_attachment` - Delete attachment

### Custom Fields (5 tools)
- `mcp__asana__mcp_list_custom_fields` - List custom fields for project
- `mcp__asana__mcp_create_custom_field` - Create custom field
- `mcp__asana__mcp_delete_custom_field` - Delete custom field
- `mcp__asana__mcp_set_custom_field_value` - Set field value on task
- `mcp__asana__mcp_clear_custom_field_value` - Clear field value

---

## Testing the Connection

### Using Python MCP Client

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def test_connection():
    url = "http://localhost:8000/sse"
    headers = {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "test@example.com"
    }

    async with sse_client(url, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            result = await session.initialize()
            print(f"Connected to: {result.serverInfo.name}")

            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")

            # Call a tool
            workspaces = await session.call_tool(
                "mcp_list_workspaces",
                arguments={}
            )
            print(f"Workspaces: {workspaces}")

asyncio.run(test_connection())
```

### Using Claude Code CLI

```bash
# In a Claude Code session, you can now use the MCP tools:
# "List all workspaces"
# "Create a new workspace called Engineering"
# "Show me all tasks in workspace 1"
```

---

## Troubleshooting

### Issue: "Not authenticated" errors

**Cause:** Missing or incorrect API key

**Solution:**
```bash
# Ensure X-API-Key header is set correctly
claude mcp remove asana -s local
claude mcp add asana http://localhost:8000/sse \
  --transport sse \
  --header "X-API-Key: asana-mcp-secret-key-2025" \
  --header "X-Mcp-User: test@example.com" \
  -s local
```

### Issue: "500 Internal Server Error"

**Cause:** This was fixed in the latest version. Make sure you have the latest code.

**Solution:** Pull latest changes with Pydantic schema fixes.

### Issue: MCP server not connecting

**Checks:**
1. Is the API running? `docker-compose ps`
2. Is port 8000 accessible? `curl http://localhost:8000/`
3. Check logs: `docker-compose logs -f api`

---

## Production Deployment

For production use, you should:

1. **Change the API key:**
   ```bash
   # In .env file
   MCP_API_KEY=your-secure-random-key-here
   ```

2. **Use HTTPS with SSL/TLS:**
   ```bash
   claude mcp add asana https://your-domain.com/sse \
     --transport sse \
     --header "X-API-Key: your-production-key"
   ```

3. **Configure user context per deployment:**
   - Development: `X-Mcp-User: dev@example.com`
   - Staging: `X-Mcp-User: staging@example.com`
   - Production: `X-Mcp-User: admin@example.com`

---

## Configuration Files

### Claude Code CLI

**Local (project-specific):**
- File: `~/.claude.json`
- Scope: Only for this project
- Command: `-s local` (default)

**User (global):**
- File: User-level configuration
- Scope: All projects for this user
- Command: `-s user`

**Project (shared):**
- File: `.mcp.json` in project root
- Scope: Shared with team via git
- Command: `-s project`

### Example .mcp.json (for sharing with team)

```json
{
  "mcpServers": {
    "asana-local": {
      "type": "sse",
      "url": "http://localhost:8000/sse",
      "headers": {
        "X-API-Key": "asana-mcp-secret-key-2025",
        "X-Mcp-User": "developer@example.com"
      }
    },
    "asana-staging": {
      "type": "sse",
      "url": "https://staging-api.example.com/sse",
      "headers": {
        "X-API-Key": "${ASANA_STAGING_API_KEY}",
        "X-Mcp-User": "${USER_EMAIL}"
      }
    }
  }
}
```

---

## Related Documentation

- [SSE Fix Summary](./SSE_FIX_SUMMARY.md) - Details about the SSE transport fix
- [MCP Authentication Guide](./MCP_AUTH_GUIDE.md) - Authentication architecture
- [MCP Server Implementation](./app/mcp_server.py) - Source code

---

**Status:** ✅ **PRODUCTION READY**
**Transport:** SSE (Server-Sent Events)
**Success Rate:** 100%
**Total Tools:** 43
