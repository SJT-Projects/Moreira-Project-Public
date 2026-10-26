"""Compatibilidad con `uvicorn main:app` desde la carpeta backend."""

from app.main import app

__all__ = ["app"]
