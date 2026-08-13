# DESPLIEGUE — Backend Turnogo (FastAPI)

> Documentación de los escenarios de ejecución posiblemente presentes en el repo. **No inventar**: se describe lo que el proyecto efectivamente contiene y lo que **no** está definido aún.
> Fuentes: `README.md`, `requirements.txt`, `app/main.py`, `supabase/config.toml`, archivos raíz (Dockerfile/docker-compose existentes pero vacíos).
> Este documento no incorpora secretos.

---

## 1. Estado de la infraestructura en el repositorio

| Recurso | Estado en el repo |
|---|---|
| Punto de entrada ASGI | Definido: `app.main:app` (`app/main.py` → `app = create_app()`, línea 64) |
| Orquestación de servidor (uvicorn/gunicorn) | No definida: no hay `start.sh`, `Procfile`, `vercel.json`, ni comando documentado |
| Docker | `Dockerfile` y `docker-compose.yml` existen en la raíz pero están **vacíos** (0 bytes) |
| Configuración Alembic | Scripts en `alembic/` pero sin `alembic.ini`/`env.py` |
| Deploy a producción | No hay configuración de hosting (no Vercel/Railway/Fly/Render/K8s manifest) en el repo |
| Migraciones Supabase | `supabase/migrations/*.sql` versionadas (esquema inicial, remote_schema, negocio_imagenes, categorias visuales, google_auth, rls_politicas) |

**Conclusión:** el repo define la aplicación y sus dependencias, pero **no** define cómo se sirve ni se publica. El README menciona Docker & Docker Compose, pero los archivos correspondientes están vacíos.

---

## 2. Desarrollo local

### 2.1 Dependencias

- `requirements.txt` incluye `uvicorn`, `fastapi`, `SQLAlchemy`, `psycopg2-binary`, `resend`, `mercadopago`, `google-auth`, `python-decouple`, etc. Recordar instalar en un entorno virtual: en la raíz existe `venv/` (ignorada por git, `.gitignore` → `venv/`, `.venv/`).

### 2.2 Variables de entorno

- Crear `.env` en la raíz con las variables documentadas en `docs/CONFIGURACION.md` (§7): obligatorias `DB`, `RESEND_API_KEY`, `MAPBOX_ACCESS_TOKEN`, `BACKEND_URL`, `MERCADOPAGO_ACCESS_TOKEN`, `GOOGLE_CLIENT_ID`; opcionales `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `TWO_FACTOR_TOKEN_EXPIRE_HOURS`, `FRONTEND_URL`.
- `python-decouple` (`config('...')` en `app/core/config.py` y `app/db/database.py`) lee `.env`.
- `.env` y `.env.*` están en `.gitignore`.

### 2.3 Base de datos local (Supabase CLI)

- `supabase/config.toml` define un stack local: Postgres en `54322`, API (PostgREST) en `54321`, Studio en `54323`, Inbucket (emails de prueba) en `54324`, Analytics en `54327`.
- Migraciones aplicables: `supabase/migrations/*.sql` (esquema inicial, remote_schema, etc.).
- `DB` apuntará a la URL local (Postgres en `54322`, `major_version = 17`).

### 2.4 Arranque del servidor

- Ejecutar el proceso ASGI vía `uvicorn` con el módulo de la app. La convención implícita en el código es:

  ```
  uvicorn app.main:app
  ```

  (El `requirements.txt` incluye `uvicorn>=0.44.0`; no hay script de arranque versionado en el repo.)

### 2.5 Verificación

- `GET /` → healthcheck con `{"mensaje": "API Turnogo funcionando"}`.
- `GET /db-test` → prueba de conexión a la BD responde `"conexion OK con postgres"`.
- Swagger/OpenAPI por defecto de FastAPI en el host local (la app se crea con `FastAPI(title="Turnogo")`).
- Para pagos en test: `MERCADOPAGO_ACCESS_TOKEN` con prefijo `TEST-` (el servicio detecta el modo test, `app/services/payment_service.py:68`).
- Emails en local: el stack de Supabase local incluye Inbucket para inspeccionar los emails; los envíos reales usan Resend (`app/services/email_service.py:11`).

---

## 3. Build

- **Backend (Python):** sin paso de build propiamente dicho en el repo (no hay `pyproject.toml`, `setup.py` ni empaquetado). La "construcción" es la instalación de dependencias (`requirements.txt`) sobre Python 3 (según README, "Python 3").
- **Docker:** `Dockerfile` vacío (0 bytes) → sin imagen de contenedor definida.
- **Frontend (React + TypeScript):** vive fuera de este backend (repo/parcela `Turnexo_front`); su build (Vite/etc.) y despliegue no se documenta aquí.
- No hay pasos de compilación de assets Python ni de migraciones automáticas de build.

---

## 4. Producción

### 4.1 Lo que existe

- Migraciones SQL versionadas en `supabase/migrations/` listas para aplicarse contra la BD remota.
- Tokens orientados a producción en `config.py`: `FRONTEND_URL` por defecto `https://www.turnogo.app` y CORS permite `https://www.turnogo.app` y `https://turnogo.app` (`app/main.py:22-26`).
- `BACKEND_URL` necesaria para que Mercado Pago llame al webhook `{BACKEND_URL}/api/pagos/webhook` (`app/services/payment_service.py:41`).
- `SECRET_KEY` debe definirse en el entorno (en el código tiene un default de ejemplo; ver `docs/CONFIGURACION.md` y `docs/SEGURIDAD.md`).

### 4.2 Lo que NO está definido (falta por agregar)

- Comando/servidor de corrida en producción (gunicorn+uvicorn, workers, etc.).
- Despliegue de la imagen Docker (Dockerfile vacío).
- Configuración de hosting (Vercel/Railway/Fly/Render) o servidor propio.
- Políticas RLS funcionales en Supabase (revisar `docs/SEGURIDAD.md`).
- Passos de CI/CD (no hay manifiestos de pipeline en el repo visible).

---

## 5. Servicios externos y su configuración en producción

| Servicio | Config necesaria | Notas de despliegue |
|---|---|---|
| Resend | `RESEND_API_KEY` | emails de verificación/OTP/reset/notificaciones |
| Mercado Pago | `MERCADOPAGO_ACCESS_TOKEN`, `BACKEND_URL`, `FRONTEND_URL` | el webhook debe ser alcanzable públicamente en `/api/pagos/webhook`; token `TEST-*` en pruebas, token real en producción |
| Google | `GOOGLE_CLIENT_ID` (y `GOOGLE_CLIENT_SECRET` definido en config) | login con Google (validación de `id_token`) |
| Mapbox | `MAPBOX_ACCESS_TOKEN` | geocoding de direcciones |
| PostgreSQL (Supabase) | `DB` | URL de conexión remota |

---

## 6. Checklist de configuración antes de desplegar

1. Definir todas las variables obligatorias de `docs/CONFIGURACION.md` §7 en el entorno (incluye `SECRET_KEY`, ahora obligatoria).
2. `SECRET_KEY` segura (sin default) y, en producción, ≥ 256 bits.
3. Aplicar las migraciones `supabase/migrations/*.sql` contra la BD remota (incluida `20260812120000_rls_politicas.sql`).
4. Asegurar que `BACKEND_URL` quede expuesta en Internet para el webhook de Mercado Pago.
5. Exponer `/` (healthcheck) y validar `/db-test`.
6. Restringir la exposición de `docs` (Swagger UI) y endpoints de prueba en producción (ver `docs/SEGURIDAD.md`).