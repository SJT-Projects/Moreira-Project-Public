"""Punto de entrada que Vercel detecta para desplegar FastAPI."""

import sys
from pathlib import Path

from fastapi.staticfiles import StaticFiles

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

PUBLIC_DIR = Path(__file__).resolve().parent / "public"
if PUBLIC_DIR.is_dir() and not any(
    getattr(route, "name", None) == "frontend" for route in app.routes
):
    app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="frontend")

__all__ = ["app"]
