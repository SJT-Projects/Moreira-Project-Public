# Despliegue de Moreira en Vercel

Vercel despliega el servicio `moreira` definido en `vercel.json`. `index.py`
expone FastAPI y sirve la compilación de `public/`. El frontend se compila con
`API_BASE_URL` vacío para que consuma la API en el mismo dominio.

## Variables privadas

Configurar en Production, Preview y Development cuando corresponda:

- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `INDICATOR_HMAC_SECRET`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `SAFE_BROWSING_API_KEY`
- `VIRUSTOTAL_API_KEY` (opcional)
- `DEFAULT_PHONE_REGION=AR`

`FIREBASE_SERVICE_ACCOUNT_JSON` debe contener el JSON completo de una cuenta de
servicio dedicada al backend. Nunca se guarda en GitHub.

## Actualizar el frontend estático

Desde `frontend/`:

```powershell
flutter build web --release --pwa-strategy=none --dart-define-from-file=dart_defines.json
```

Después se reemplaza el contenido de `public/` por `frontend/build/web/` y se
sube el cambio. Vercel vuelve a desplegar automáticamente la rama principal.
