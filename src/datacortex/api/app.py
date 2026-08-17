"""FastAPI application for Datacortex."""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import graph, nodes, pulse, files, terminal

logger = logging.getLogger(__name__)

# --- Bearer token auth ---

_api_token: Optional[str] = None
_auth_enabled: bool = False


def _init_auth():
    """Initialize auth state from environment."""
    global _api_token, _auth_enabled
    _api_token = os.environ.get("DATACORTEX_API_TOKEN")
    if _api_token:
        _auth_enabled = True
        logger.info("DATACORTEX_API_TOKEN is set — bearer auth enabled")
    else:
        _auth_enabled = False
        logger.warning(
            "DATACORTEX_API_TOKEN is not set — all requests allowed (local dev mode)"
        )


def verify_bearer_token(request: Request):
    """FastAPI dependency: require valid bearer token when auth is enabled."""
    if not _auth_enabled:
        return  # no token configured — allow all
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and auth_header[7:] == _api_token:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


# --- App setup ---

app = FastAPI(
    title="Datacortex",
    description="Knowledge Graph Visualization for Datacore",
    version="0.1.0",
    redirect_slashes=False,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    _init_auth()


# Health endpoint — no auth required
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# API routes — all require auth
auth_deps = [Depends(verify_bearer_token)]
app.include_router(graph.router, prefix="/api/graph", tags=["graph"], dependencies=auth_deps)
app.include_router(pulse.router, prefix="/api/pulse", tags=["pulse"], dependencies=auth_deps)
app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"], dependencies=auth_deps)
app.include_router(files.router, prefix="/api/files", tags=["files"], dependencies=auth_deps)
app.include_router(terminal.router, prefix="/api/terminal", tags=["terminal"], dependencies=auth_deps)


# Serve frontend static files
# Try to find frontend directory relative to package
frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
