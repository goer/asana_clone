"""Application entry-point."""
from fastapi import FastAPI

from app.routers import api_router

app = FastAPI(title="Asana Clone API")
app.include_router(api_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "Welcome to the Asana Clone API"}
