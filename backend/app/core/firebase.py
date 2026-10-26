import logging
import threading
from typing import Any

import firebase_admin
from firebase_admin import auth, firestore

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_initialization_error: str | None = None


def firebase_status() -> tuple[bool, str]:
    global _initialization_error
    settings = get_settings()
    if not settings.firebase_project_id:
        return False, "FIREBASE_PROJECT_ID no está configurado."
    if not settings.indicator_hmac_secret:
        return False, "INDICATOR_HMAC_SECRET no está configurado."
    try:
        get_firestore_client()
        return True, "conectado"
    except Exception:
        logger.warning("No se pudo comprobar Firestore: %s", _initialization_error or "Error de configuración")
        return False, _initialization_error or "Firebase Admin no está disponible."


def _get_app() -> firebase_admin.App:
    global _initialization_error
    settings = get_settings()
    if not settings.firebase_project_id:
        raise RuntimeError("FIREBASE_PROJECT_ID no está configurado.")

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    with _lock:
        try:
            return firebase_admin.get_app()
        except ValueError:
            try:
                app = firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
                _initialization_error = None
                return app
            except Exception as exc:
                _initialization_error = f"No se pudo iniciar Firebase Admin ({type(exc).__name__})."
                raise RuntimeError(_initialization_error) from exc


def get_firestore_client() -> Any:
    if not get_settings().indicator_hmac_secret:
        raise RuntimeError("INDICATOR_HMAC_SECRET no está configurado.")
    return firestore.client(app=_get_app())


def verify_user_token(token: str) -> dict[str, Any]:
    # Los tokens nuevos pueden diferir unos segundos del reloj local. Una
    # tolerancia mínima evita rechazos espurios sin debilitar la autenticación.
    return auth.verify_id_token(
        token,
        app=_get_app(),
        check_revoked=True,
        clock_skew_seconds=5,
    )


def ensure_admin_claims(uid: str) -> bool:
    """Lee el rol desde Firebase Auth; el cliente nunca elige su rol."""
    user = auth.get_user(uid, app=_get_app())
    return user.custom_claims is not None and user.custom_claims.get("admin") is True
