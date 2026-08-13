# CONFIGURACIÓN — Backend Turnogo (FastAPI)

> Toda la configuración se lee de variables de entorno mediante `python-decouple` (`app/core/config.py` y `app/db/database.py`).
> Este documento **no muestra valores**: solo nombres de variables, su uso en el código y si son obligatorias u opcionales.
> Fuente: `app/core/config.py`, `app/main.py`, `app/db/database.py`, `supabase/config.toml`, `requirements.txt`.

---

## 1. Variables de entorno

### 1.1 Definidas en `app/core/config.py`

| Variable | Uso en código | ¿Obligatoria? | Descripción |
|---|---|---|---|
| `SECRET_KEY` | `config.py:4` | **Obligatoria** | Clave de firma HS256 de los JWT. `decouple.config("SECRET_KEY")` sin default: la app no arranca si no está definida (se eliminó el valor de ejemplo "change-this-secret-in-production"). |
| `ALGORITHM` | `config.py:5` | Constante `"HS256"` en el código | No es variable de entorno; se fija el algoritmo de firma. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `config.py:6` | Opcional (default `60`) | Minutos de validez del access token. `int(decouple.config(...))`. |
| `TWO_FACTOR_TOKEN_EXPIRE_HOURS` | `config.py:7` | Opcional (default `9`) | Horas de vigencia del OTP 2FA y del token "recordar 2FA". |
| `RESEND_API_KEY` | `config.py:8`, `email_service.py:11` | Obligatoria | Clave de la API de Resend usada para emails (verificación, OTP, reset). |
| `FRONTEND_URL` | `config.py:9` | Opcional (default `https://www.turnogo.app`) | URL base del frontend. Se usa en enlaces de email (`email_service.py:21,56`), URLs de retorno de pagos (`payment_service.py:36-38`) y URLs de QR (`qr_service.py:10`). |
| `MAPBOX_ACCESS_TOKEN` | `config.py:10`, `mapbox_service.py:31` | Obligatoria | Token de acceso a la API de geocoding de Mapbox. |
| `BACKEND_URL` | `config.py:11`, `payment_service.py:41` | Obligatoria | URL base del backend. Se usa como `notification_url` del webhook de Mercado Pago (`payment_service.py:41`). |
| `MERCADOPAGO_ACCESS_TOKEN` | `config.py:12`, `payment_service.py:14,68` | Obligatoria | Access token de Mercado Pago. El código detecta modo test si la cadena empieza con `TEST-` (`payment_service.py:68`). |
| `GOOGLE_CLIENT_ID` | `config.py:13`, `auth_service.py:533-538` | Obligatoria | Client ID de Google OAuth, usado para verificar el `id_token` del login con Google. |
| `GOOGLE_CLIENT_SECRET` | `config.py:14` | Configurada (sin uso directo detectado) | Secret de Google OAuth; definido en config pero el flujo actual de login con Google solo consume `GOOGLE_CLIENT_ID` (`auth_service.py:524`). |

### 1.2 Definida en `app/db/database.py`

| Variable | Uso en código | ¿Obligatoria? | Descripción |
|---|---|---|---|
| `DB` | `database.py:8` | Obligatoria | URL de conexión a PostgreSQL (`decouple.config('DB')`). Se pasa directo a `SQLAlchemy.create_engine`. |

### 1.3 Notas

- No existe `env.example` ni `.env.example` versionado en el repo.
- `.gitignore` excluye `.env` y `.env.*` (los secretos no se comitean).
- La configuración usa `python-decouple`; las variables que no tienen default (`RESEND_API_KEY`, `MAPBOX_ACCESS_TOKEN`, `BACKEND_URL`, `MERCADOPAGO_ACCESS_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `DB`) hacen fallar el arranque si no están definidas.

---

## 2. Configuración de la aplicación FastAPI

Definida en `app/main.py`:

- **Título de la API:** `FastAPI(title="Turnogo")` (`main.py:20`).
- **CORS** (`main.py:22-34`): orígenes `http://localhost:5173`, `https://www.turnogo.app`, `https://turnogo.app`; `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
- **Healthchecks** (`main.py:36-46`):
  - `GET /` → `{"mensaje": "API Turnogo funcionando"}`.
  - `GET /db-test` → ejecuta `SELECT ...` contra la BD (usa `app.db.database.engine`) y responde `"conexion OK con postgres"`.
- **Routers montados con prefijo `/api`** (`main.py:48-60`): usuario, auth, turnos, empleados, servicios, negocios, categorias, clientes, horarios, georef, planes, estadistica, pagos.
- **Modelo de creación:** patrón `create_app()` y módulo con `app = create_app()` como instancia a nivel de módulo (`main.py:64`). Punto de entrada ASGI: `app.main:app`.

No hay configuración adicional de tuplas de workers, timeout, SSL ni cabeceras de seguridad en el código de la app.

---

## 3. PostgreSQL y SQLAlchemy

`app/db/database.py`:

- **URL de conexión:** desde la variable `DB` (`database.py:8`).
- **Pool de conexiones:** `pool_pre_ping=True`, `pool_recycle=300`, `pool_size=5`, `max_overflow=10` (`database.py:10-16`).
- **Session factory:** `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)` (`database.py:18-22`).
- **Prueba de conexión al importar:** `SELECT 1` en un `try/except OperationalError` que silencia el error (`database.py:25-29`).
- **Dependencias de tipo:** `get_db` definido en `app/core/dependencies.py` y una versión equivalente en `app/db/session.py` (usada por `usuario_router.py:4`).
- **Drivers:** `psycopg2-binary` y `SQLAlchemy>=2.0.49` en `requirements.txt`.
- **Base declarativa:** `app/db/base.py` define `Base = declarative_base()`.

---

## 4. Supabase

- **Proyecto (config local):** `supabase/config.toml`: `project_id = "TurnoGo"`.
- **Migraciones:** carpeta `supabase/migrations/` con scripts SQL versionados (001-esquema inicial, remote_schema, negocio_imagenes, categorias visuales, google auth).
- **Seed (local):** `supabase/db.seed.sql_paths = ["./seed.sql"]`.
- **Servicios locales del CLI de Supabase** (puertos definidos en `config.toml`):
  - API (PostgREST): puerto `54321`; schemas expuestos `public` y `graphql_public`; `max_rows = 1000`.
  - PostgreSQL local: puerto `54322`, `major_version = 17`.
  - Studio: puerto `54323`.
  - Inbucket (buzón de emails local): puerto `54324`.
  - Analytics: puerto `54327`.
- **Auth local (config.toml):** `site_url = "http://127.0.0.1:3000"`, `jwt_expiry = 3600`, `otp_expiry = 3600`, `otp_length = 6`, `enable_signup = true`. (La app Python gestiona su propio auth con JWT; ver `docs/AUTENTICACION.md`.)
- **Conexión de la app:** la app conecta a la BD por **URL directa** (`config('DB')`), no vía PostgREST/anon.
- **Alembic:** existe la carpeta `alembic/` con scripts de migración en Python, pero en el repo no hay `alembic.ini` ni `env.py`, por lo que no hay setup Alembic ejecutable.

---

## 5. Dependencias (`requirements.txt`)

Backend y servicios:

- **Web:** `fastapi`, `uvicorn`, `python-multipart`, `htmltools`/`httptools`, `h11`, `anyio`.
- **Base de datos:** `sqlalchemy`, `psycopg2-binary`.
- **Auth:** `bcrypt`, `passlib`, `pyjwt`, `python-jose`, `google-auth`, `email-validator`.
- **Config:** `python-decouple`, `python-dotenv`.
- **Servicios externos:** `resend` (emails), `mercadopago==3.3.0` (pagos), `requests` y `aiohttp`/`aiohttp-retry` (HTTP), `qrcode[pil]` (QR).
- **Validación/otros:** `pydantic`, `pydantic_core`, `email-validator`, `PyYAML`, `cryptography`.
- **Dev:** `pylint` (etiquetado como `# Dev`).

---

## 6. Servicios externos

| Servicio | Librería/fuente | Config usada | Uso |
|---|---|---|---|
| Resend | `resend` (`email_service.py:11`) | `RESEND_API_KEY` | emails de verificación, OTP 2FA, reset de contraseña, notificaciones de turno |
| Mercado Pago | `mercadopago` SDK (`payment_service.py:14`) | `MERCADOPAGO_ACCESS_TOKEN`, `BACKEND_URL`, `FRONTEND_URL` | preferencia de pago, webhook `notification_url` en `/api/pagos/webhook`, URLs de retorno, detección de modo test `TEST-*` |
| Google | `google-auth` (`auth_service.py:524-537`) | `GOOGLE_CLIENT_ID` | validación del `id_token` de login social |
| Mapbox | `requests` → Mapbox Geocoding API (`mapbox_service.py:26-36`) | `MAPBOX_ACCESS_TOKEN` | geocoding (timeout 10 s) |
| QR (local) | `qrcode` (`qr_service.py`) | `FRONTEND_URL` | QR con enlace `{FRONTEND_URL}/dashboard/turnos?turno={id}` |

---

## 7. Configuración necesaria para levantar la app

Requerida (sin default):

1. `DB` — URL de conexión PostgreSQL.
2. `SECRET_KEY` — clave de firma de JWT (antes tenía default inseguro; ahora necesaria para arrancar).
3. `RESEND_API_KEY` — emails.
4. `MAPBOX_ACCESS_TOKEN` — geocoding.
5. `BACKEND_URL` — URL pública del backend (para el webhook de pagos).
6. `MERCADOPAGO_ACCESS_TOKEN` — pagos (token `TEST-*` para pruebas).
7. `GOOGLE_CLIENT_ID` — login con Google (y `GOOGLE_CLIENT_SECRET`, definido en config aunque el flujo actual no lo consume).

Opcional (con default en código):

8. `ACCESS_TOKEN_EXPIRE_MINUTES` — default `60`.
9. `TWO_FACTOR_TOKEN_EXPIRE_HOURS` — default `9`.
10. `FRONTEND_URL` — default `https://www.turnogo.app`.

Interrelación `FRONTEND_URL`/`BACKEND_URL`:

- `FRONTEND_URL`: enlaces en emails, URLs de retorno de Mercado Pago y de los QR.
- `BACKEND_URL`: `notification_url` (webhook) de la preferencia de pago → `{BACKEND_URL}/api/pagos/webhook`.