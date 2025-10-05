"""Application entry-point."""
import logging
import os

from fastapi import FastAPI
from starlette.routing import Mount

logger = logging.getLogger(__name__)

from app.routers import api_router

app = FastAPI(title="Asana Clone API")
app.include_router(api_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "Welcome to the Asana Clone API"}


enable_mcp = os.getenv("ENABLE_MCP", "1") not in {"0", "false", "False"}

if enable_mcp:
    try:
        # Create MCP server with simplified schemas to avoid recursion issues
        from app.mcp_server import create_mcp_server

        mcp_app = create_mcp_server()
        if mcp_app:
            # Mount the MCP app at /mcp-api
            app.mount("/mcp-api", mcp_app)
            logger.info("✓ MCP server mounted at /mcp-api with HTTP and SSE transports")
        else:
            logger.warning("✗ MCP server creation failed, continuing without MCP")
    except ImportError:
        logger.info("fastapi-mcp not available; skipping MCP integration")
    except Exception as e:
        logger.error(f"Unexpected error setting up MCP: {type(e).__name__}: {e}")
else:
    logger.info("MCP disabled via ENABLE_MCP environment variable")
