import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.analysis import router as analysis_router
from app.api.academy import router as academy_router
from app.api.indicators import router as indicators_router
from app.api.reports import admin_router, router as reports_router
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
# httpx incluye la URL completa en INFO. Safe Browsing autentica con un parámetro
# de consulta, por lo que esos logs revelarían la clave del servidor.
logging.getLogger("httpx").setLevel(logging.WARNING)
settings = get_settings()

app = FastAPI(
    title="Moreira · Detector Anti-Estafas",
    description=(
        "Analiza mensajes y enlaces usando reglas explícitas, antecedentes comunitarios "
        "y proveedores de contexto opcionales. Un resultado bajo no garantiza que un "
        "mensaje o enlace sea seguro."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(analysis_router)
app.include_router(academy_router)
app.include_router(indicators_router)
app.include_router(reports_router)
app.include_router(admin_router)


@app.get("/health", tags=["Estado"], summary="Muestra el estado de configuración")
async def health() -> dict:
    from app.core.firebase import firebase_status

    firebase_ready, _ = firebase_status()
    return {
        "api": "ok",
        "firestore": "configurado" if firebase_ready else "requiere_configuracion",
        "groq": "configurado" if bool(settings.groq_api_key) else "requiere_configuracion",
        "reputacion_urls": (
            "configurada" if settings.safe_browsing_api_key else "requiere_configuracion"
        ),
        "virustotal": (
            "configurado" if settings.virustotal_api_key else "requiere_configuracion"
        ),
    }


# En producción temporal y demostraciones, el mismo proceso sirve Flutter y la
# API. De esta forma una única URL HTTPS funciona detrás de Cloudflare Tunnel.
frontend_build = Path(__file__).resolve().parents[2] / "frontend" / "build" / "web"
if frontend_build.is_dir():
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="frontend")
