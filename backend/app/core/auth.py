import asyncio
import logging
from typing import Annotated, Any

from firebase_admin import auth as firebase_auth
from firebase_admin import exceptions as firebase_exceptions
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.firebase import ensure_admin_claims, verify_user_token

_bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def _auth_error(status_code: int, code: str, message: str) -> HTTPException:
    """Devuelve errores identificables sin revelar datos internos de Firebase."""
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "auth_required",
            "Iniciá sesión para continuar.",
        )
    try:
        return await asyncio.to_thread(verify_user_token, credentials.credentials)
    except firebase_auth.ExpiredIdTokenError as exc:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "auth_session_expired",
            "La sesión venció. Volvé a iniciar sesión.",
        ) from exc
    except firebase_auth.RevokedIdTokenError as exc:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "auth_session_revoked",
            "La sesión fue cerrada o revocada. Volvé a iniciar sesión.",
        ) from exc
    except firebase_auth.UserDisabledError as exc:
        raise _auth_error(
            status.HTTP_403_FORBIDDEN,
            "auth_user_disabled",
            "La cuenta está deshabilitada.",
        ) from exc
    except (firebase_auth.InvalidIdTokenError, ValueError) as exc:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "auth_invalid_token",
            "No pudimos validar la sesión. Cerrá sesión e ingresá nuevamente.",
        ) from exc
    except firebase_auth.CertificateFetchError as exc:
        logger.warning("Firebase Authentication no pudo descargar certificados: %s", exc)
        raise _auth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "auth_provider_unavailable",
            "Firebase Authentication no está disponible en este momento.",
        ) from exc
    except (firebase_auth.UnexpectedResponseError, firebase_exceptions.FirebaseError) as exc:
        logger.warning("Firebase Authentication respondió con un error: %s", exc)
        raise _auth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "auth_provider_unavailable",
            "Firebase Authentication no está disponible en este momento.",
        ) from exc
    except Exception as exc:
        # No registramos el token; solo el fallo del proveedor para diagnóstico.
        logger.exception("No se pudo verificar el token de Firebase")
        raise _auth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "auth_verification_failed",
            "El servidor no pudo verificar la sesión. Volvé a intentar en unos segundos.",
        ) from exc


async def admin_user(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    try:
        allowed = await asyncio.to_thread(ensure_admin_claims, user["uid"])
    except Exception as exc:
        raise _auth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "admin_verification_failed",
            "No se pudo verificar el rol de administrador.",
        ) from exc
    if not allowed:
        raise _auth_error(
            status.HTTP_403_FORBIDDEN,
            "admin_required",
            "Se requiere el rol de administrador.",
        )
    return user


AuthenticatedUser = Annotated[dict[str, Any], Depends(current_user)]
AdminUser = Annotated[dict[str, Any], Depends(admin_user)]
