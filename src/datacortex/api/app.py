"""FastAPI application for Datacortex."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import graph, nodes, pulse

app = FastAPI(
    title="Datacortex",
    description="Knowledge Graph Visualization for Datacore",
    version="0.1.0",
    redirect_slashes=False,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(pulse.router, prefix="/api/pulse", tags=["pulse"])
app.include_router(nodes.router, prefix="/api/nodes", tags=["nodes"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Serve frontend static files
# Try to find frontend directory relative to package
frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
