"""Concede el claim admin a una cuenta existente; ejecutar solo por el operador."""

import argparse

import firebase_admin
from firebase_admin import auth

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Concede el rol administrativo de Moreira.")
    parser.add_argument("email", help="Correo exacto de una cuenta ya registrada en Firebase Auth")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.firebase_project_id:
        parser.error("Configurá FIREBASE_PROJECT_ID en backend/.env.")

    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
    user = auth.get_user_by_email(args.email.strip(), app=app)
    claims = dict(user.custom_claims or {})
    claims["admin"] = True
    auth.set_custom_user_claims(user.uid, claims, app=app)
    print(f"Rol de administrador concedido a {user.email}. Cerrá sesión y volvé a ingresar para actualizar el token.")


if __name__ == "__main__":
    main()
