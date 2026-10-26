# Moreira · Detector Anti-Estafas

Aplicación Flutter Web con una API FastAPI. Los reportes e indicadores se guardan en Cloud Firestore; la clave de Groq y las credenciales administrativas de Firebase pertenecen exclusivamente al servidor Python.

El frontend de Flutter que se debe ejecutar está en `frontend/`. El backend está en `backend/`.

**Guía paso a paso para Windows + VS Code:** [docs/GUIA_EJECUCION_LOCAL.md](docs/GUIA_EJECUCION_LOCAL.md).

**Despliegue público en Vercel:** [docs/DESPLIEGUE_VERCEL.md](docs/DESPLIEGUE_VERCEL.md). El directorio `public/` contiene la compilación web que Vercel sirve y `index.py` expone FastAPI en el mismo dominio.

## Configurar la API local

Requiere Python 3.11 o superior. Desde PowerShell, en la raíz del repositorio:

```powershell
Set-Location backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configurá en `backend/.env` el ID de tu proyecto Firebase, una clave HMAC aleatoria para los identificadores privados, una clave de Groq y una API key habilitada para Safe Browsing. Opcionalmente, agregá una clave pública de VirusTotal para complementar la reputación de enlaces. Por ejemplo, generá una clave HMAC con:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Guardá el resultado en `INDICATOR_HMAC_SECRET` en `backend/.env`. Nunca lo uses en Flutter ni lo subas al repositorio.

En Firebase, habilitá Authentication con correo y contraseña y creá **una base Cloud Firestore**. Para desarrollo local, la CLI de Google puede proporcionar las credenciales Application Default Credentials que usa Firebase Admin con `gcloud auth application-default login`.

El proceso Python necesita permisos IAM para leer y escribir Firestore. Firebase Admin verifica los tokens de sesión de Authentication. El cliente Flutter no obtiene acceso directo a las colecciones. El archivo `backend/firestore.rules` bloquea el acceso directo y `backend/firestore.indexes.json` define los índices para las consultas comunitarias.

Desplegá las reglas e índices desde la raíz con Firebase CLI, después de asociar el proyecto correcto:

```powershell
firebase deploy --project TU_PROJECT_ID --only firestore:rules,firestore:indexes
```

Para crear la primera cuenta administradora, registrá primero su correo desde la aplicación e iniciá sesión al menos una vez. Luego, desde `backend/` y con credenciales IAM autorizadas, ejecutá:

```powershell
python -m app.scripts.set_admin correo@ejemplo.com
```

El claim se concede desde el servidor; la cuenta debe cerrar sesión y volver a ingresar para recibir el nuevo token. Los intentos educativos se califican en la API y el progreso queda vinculado al UID autenticado.

Groq ofrece el análisis de contexto con su modelo de salida estructurada. Safe Browsing aporta reputación de URLs. VirusTotal complementa esa verificación consultando reportes existentes, sin enviar automáticamente enlaces nuevos a escanear. La integración guarda resultados temporalmente y limita las consultas para respetar la cuota pública. Un fallo de VirusTotal no reemplaza ni invalida las comprobaciones principales. Revisá las condiciones y los cupos actuales de los proveedores en sus consolas.

Iniciá FastAPI desde `backend/`:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

La verificación de estado está en `http://127.0.0.1:8000/health`, y la documentación interactiva de FastAPI en `http://127.0.0.1:8000/docs`.

## Configurar y ejecutar Flutter Web

En Firebase, registrá una aplicación web para el mismo proyecto. Los campos `apiKey`, `appId`, `messagingSenderId`, `projectId` y `authDomain` que requiere Firebase Web son configuración pública de cliente; los datos se protegen con Authentication, las reglas y los permisos del servidor.

Ejecutá este comando desde `frontend/` después de sustituir los valores por los de tu aplicación web Firebase:

```powershell
flutter run -d web-server --web-hostname localhost --web-port 60891 --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=FIREBASE_API_KEY=REEMPLAZAR --dart-define=FIREBASE_APP_ID=REEMPLAZAR --dart-define=FIREBASE_MESSAGING_SENDER_ID=REEMPLAZAR --dart-define=FIREBASE_PROJECT_ID=REEMPLAZAR --dart-define=FIREBASE_AUTH_DOMAIN=REEMPLAZAR
```

Si es la primera ejecución o cambiaste dependencias, ejecutá `flutter pub get` desde `frontend/` antes de iniciar la aplicación.

El frontend y el backend usan orígenes locales configurados explícitamente. Si cambiás el puerto o el host, agregalo a `ALLOWED_ORIGINS` en `backend/.env`.

Iniciá sesión o creá un usuario de prueba. Los endpoints de análisis y de creación de reportes requieren una sesión verificada. La lista comunitaria aprobada es de lectura pública; los datos privados de los reportes y las acciones de moderación requieren el rol de administrador configurado en Firebase Authentication.
