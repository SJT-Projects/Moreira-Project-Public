# Moreira · Detector Anti-Estafas

Proyecto escolar (alumnos de 6to año de secundaria técnica en informática). App que detecta estafas en mensajes y links.

## Reglas de trabajo

- Responder siempre en español (rioplatense).
- Respetar el objetivo del proyecto y lo que ya funciona. No reemplazar decisiones del repo por las del plan conceptual (por ejemplo: el repo usa Groq, no OpenAI; las colecciones son `reportes`, `indicadores`, etc.).
- Si faltan datos (claves, configuración de Firebase), preguntar. No inventar valores.
- Avisar antes de borrar algo relevante. Hay un proyecto Flutter vacío en la raíz (`pubspec.yaml`, `android/`, `ios/`, `web/`, `windows/`) y archivos sin uso (`frontend/lib/services/firebase_service.dart`, `backend/utils/`): no borrarlos sin consultar.
- Nunca poner claves ni secretos en el repo. Van en `backend/.env` y `frontend/dart_defines.json` (ambos ignorados por Git).
- Los cambios se suben en una rama y un Pull Request, no directo a `main`.
- Cuidar la UX para adultos mayores: botones grandes, tipografía de 18px o más, paleta tipo semáforo.

## Estructura

- `frontend/`: Flutter Web (la app real). Pantallas: Analizador, Comunidad, Academia.
- `backend/`: FastAPI (`backend/app`). Firebase Admin (Auth y Firestore), Groq para el análisis de contexto y Google Safe Browsing para URLs.
- `docs/GUIA_EJECUCION_LOCAL.md`: cómo ejecutar todo en Windows + VS Code.

## Comandos

- Backend (desde `backend/`, con `.venv` activo): `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`
- Tests del backend: `python -m pytest` desde `backend/`.
- Frontend (desde `frontend/`): `flutter pub get` y `flutter run -d chrome --web-hostname localhost --web-port 60891 --dart-define-from-file=dart_defines.json`
- En VS Code: Ejecutar y depurar → "Moreira completo (backend + frontend)".
