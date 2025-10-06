"""Application entry-point."""
import logging
import os

from fastapi import FastAPI

logger = logging.getLogger(__name__)

from app.routers import api_router

app = FastAPI(title="Asana Clone API")
app.include_router(api_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "Welcome to the Asana Clone API"}


# MCP Integration using fastapi-mcp library
# Uses a separate simplified FastAPI app to avoid recursion with complex schemas
enable_mcp = os.getenv("ENABLE_MCP", "1") not in {"0", "false", "False"}

if enable_mcp:
    try:
        from app.mcp_server import create_mcp_server

        # Create MCP server with simplified schemas (separate app)
        # This follows the recommended approach for complex APIs with nested models
        mcp = create_mcp_server()
        if mcp:
            # Mount using HTTP transport to the main app (recommended by fastapi-mcp)
            # Per fastapi-mcp docs: mount_http(router) mounts to specified router/app
            # We mount to the main app so MCP is available at /mcp
            mcp.mount_http(app)
            logger.info("✓ MCP server mounted at /mcp using HTTP transport")
            logger.info("✓ All API endpoints exposed as MCP tools")
        else:
            logger.warning("✗ MCP server creation failed, continuing without MCP")
    except ImportError:
        logger.info("fastapi-mcp not available; skipping MCP integration")
    except Exception as e:
        logger.error(f"Unexpected error setting up MCP: {type(e).__name__}: {e}")
else:
    logger.info("MCP disabled via ENABLE_MCP environment variable")
