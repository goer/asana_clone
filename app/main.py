"""Application entry-point."""
import logging
import os

from fastapi import FastAPI

try:  # Optional dependency
    from fastapi_mcp import FastApiMCP
except ImportError:  # pragma: no cover - executed only when package missing
    FastApiMCP = None


logger = logging.getLogger(__name__)

from app.routers import api_router

app = FastAPI(title="Asana Clone API")
app.include_router(api_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "Welcome to the Asana Clone API"}


enable_mcp = os.getenv("ENABLE_MCP", "1") not in {"0", "false", "False"}

if FastApiMCP is not None and enable_mcp:
    mcp = FastApiMCP(
        app,
        name="Asana Clone MCP",
        description="Model Context Protocol interface for the Asana Clone API",
    )
    mcp.mount_http()
    mcp.mount_sse()
else:  # pragma: no cover - optional dependency missing in constrained environments
    logger.info("fastapi-mcp unavailable or disabled; skipping MCP transport mounts.")
