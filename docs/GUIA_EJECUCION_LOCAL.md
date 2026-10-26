# Guía: ejecutar Moreira en tu máquina (Windows + VS Code)

Moreira tiene dos partes que corren al mismo tiempo:

| Parte | Carpeta | Tecnología | Dirección local |
|---|---|---|---|
| Backend (el "cerebro") | `backend/` | Python + FastAPI | http://127.0.0.1:8000 |
| Frontend (lo que ve el usuario) | `frontend/` | Flutter Web | http://localhost:60891 |

Firebase guarda los usuarios (Authentication) y los datos (Firestore). Groq hace el análisis con IA, Google Safe Browsing revisa los links y VirusTotal puede aportar una segunda fuente de reputación. **Groq, Safe Browsing y VirusTotal usan claves separadas**. VirusTotal es complementario: si no se configura, las comprobaciones existentes siguen funcionando.

> Importante: el `pubspec.yaml`, `android/`, `ios/`, `web/` y `windows/` que están en la **raíz** del repo son un proyecto Flutter vacío que sobró. La app real está en `frontend/`. Abrí siempre `frontend/` para Flutter.

---

## 1. Instalar los programas (una sola vez)

1. **Git**: https://git-scm.com/download/win
2. **VS Code**: https://code.visualstudio.com
3. **Flutter SDK** (incluye Dart): https://docs.flutter.dev/get-started/install/windows/web
   - El proyecto pide **Dart 3.12.1 o superior**, así que instalá el Flutter estable más reciente.
   - Comprobá en una terminal nueva: `flutter --version` y `flutter doctor`. Para web solo necesitás que aparezca **Chrome** con tilde verde; los errores de Android Studio o Visual Studio se pueden ignorar.
4. **Python 3.11 o 3.12**: https://www.python.org/downloads/ (marcá "Add python to PATH").
5. **Google Cloud CLI** (`gcloud`): https://cloud.google.com/sdk/docs/install — el backend lo usa para obtener permisos de Firebase en tu PC.
6. **Firebase CLI** (opcional, para subir reglas e índices): `npm install -g firebase-tools` (necesita Node.js).

Al abrir el repo en VS Code, aceptá instalar las **extensiones recomendadas** (Flutter, Dart, Python, Python Debugger).

## 2. Clonar el repo

```powershell
git clone https://github.com/SJT-Projects/Moreira-Project.git
cd Moreira-Project
code .
```

## 3. Configurar Firebase (una sola vez por proyecto Firebase)

En https://console.firebase.google.com, con el proyecto de Moreira:

1. **Authentication → Sign-in method →** habilitá **Correo electrónico/contraseña**.
2. **Firestore Database →** crear base de datos (modo producción está bien: el backend accede con permisos de administrador, y `backend/firestore.rules` bloquea el acceso directo desde el navegador).
3. **Configuración del proyecto → General → Tus apps →** agregá una **app Web** (icono `</>`). Copiá los valores `apiKey`, `appId`, `messagingSenderId`, `projectId` y `authDomain`. Son datos públicos de cliente, no secretos.
4. (Opcional, recomendado) Subí reglas e índices desde la raíz del repo:
   ```powershell
   firebase login
   firebase deploy --project TU_PROJECT_ID --only firestore:rules,firestore:indexes
   ```

Colecciones que crea el backend automáticamente: `reportes`, `reportes_privados`, `indicadores`, `cuotas_reportes`, `moderaciones`, `intentos_educativos`, `progreso_educativo`. No hace falta crearlas a mano.

## 4. Backend (FastAPI)

En una terminal de VS Code (PowerShell), desde la raíz:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

> Si PowerShell no deja activar el entorno, ejecutá una vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Editá `backend/.env` (este archivo **nunca** se sube a GitHub):

| Variable | Qué poner | ¿Obligatoria? |
|---|---|---|
| `FIREBASE_PROJECT_ID` | El ID del proyecto Firebase | Sí |
| `INDICATOR_HMAC_SECRET` | Una clave aleatoria: `python -c "import secrets; print(secrets.token_hex(32))"` | Sí |
| `GROQ_API_KEY` | Clave de https://console.groq.com/keys | No (sin ella no hay análisis de IA) |
| `SAFE_BROWSING_API_KEY` | API key de Google Cloud con "Safe Browsing API" habilitada | No |
| `VIRUSTOTAL_API_KEY` | Clave pública de https://www.virustotal.com/gui/my-apikey | No |
| El resto | Dejar como está | — |

Dale permisos de Firebase a tu PC (abre el navegador para iniciar sesión con la cuenta de Google dueña del proyecto):

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project TU_PROJECT_ID
```

Iniciá el backend:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Comprobá http://127.0.0.1:8000/health. Lo ideal es ver `"firestore": "configurado"`. La documentación interactiva está en http://127.0.0.1:8000/docs.

Tests (opcional): `python -m pip install pytest` y luego `python -m pytest`.

## 5. Frontend (Flutter Web)

En **otra** terminal, desde la raíz:

```powershell
cd frontend
flutter pub get
Copy-Item dart_defines.example.json dart_defines.json
```

Editá `frontend/dart_defines.json` con los valores de la app Web del paso 3 (este archivo tampoco se sube a GitHub). Después:

```powershell
flutter run -d chrome --web-hostname localhost --web-port 60891 --dart-define-from-file=dart_defines.json
```

El puerto **60891** importa: el backend solo acepta pedidos de los orígenes listados en `ALLOWED_ORIGINS` de `backend/.env`. Si cambiás el puerto, agregalo ahí.

## 6. Atajo en VS Code: botón ▶

El repo trae `.vscode/launch.json`. En la pestaña **Ejecutar y depurar** (Ctrl+Shift+D) elegí:

- **Moreira completo (backend + frontend)**: arranca los dos a la vez.
- O cada uno por separado: **Backend (FastAPI)** / **Frontend (Flutter Web)**.

Requiere haber hecho una vez los pasos 4 y 5 (entorno `.venv`, `.env` y `dart_defines.json`).

## 7. Primer uso y cuenta administradora

1. En la app, **creá una cuenta** con correo y contraseña e iniciá sesión.
2. Para moderar reportes comunitarios, convertí esa cuenta en admin (desde `backend/`, con el `.venv` activo):
   ```powershell
   python -m app.scripts.set_admin tu-correo@ejemplo.com
   ```
3. Cerrá sesión y volvé a entrar para que tome el rol.

## 8. Problemas comunes

| Síntoma | Causa probable |
|---|---|
| Pantalla "Configurar la aplicación" | Falta `dart_defines.json` o tiene valores `REEMPLAZAR`. |
| "No se pudo conectar con la API" | El backend no está corriendo, o el puerto del frontend no está en `ALLOWED_ORIGINS`. |
| `/health` muestra `firestore: requiere_configuracion` | Falta `FIREBASE_PROJECT_ID`/`INDICATOR_HMAC_SECRET`, no corriste `gcloud auth application-default login`, o la base Firestore no existe. |
| Error 401 al analizar | La sesión venció: cerrá sesión y volvé a entrar. |
| Análisis "parcial" | Falta `GROQ_API_KEY`, `SAFE_BROWSING_API_KEY` o falló una comprobación principal. VirusTotal es complementario y no vuelve parcial el análisis por sí solo. |
| `flutter pub get` pide otra versión de Dart | Actualizá Flutter: `flutter upgrade`. |
