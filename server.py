"""Vercel entrypoint: FastAPI app serving API + static SPA from web/dist."""
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from api.main import app

# Serve SPA static files (must be after API routes so /api/* is handled first)
dist = Path(__file__).parent / "web" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
