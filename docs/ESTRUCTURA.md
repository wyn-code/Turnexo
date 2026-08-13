# Estructura del repositorio — Backend TurnoGo

Descripción verificada de las carpetas y archivos importantes del backend.

## Árbol general

```
Turnexo/
├── app/                          # Código de la aplicación FastAPI
│   ├── __init__.py
│   ├── main.py                   # create_app(), CORS, healthchecks, montaje de routers
│   ├── core/                     # Infraestructura transversal
│   ├── db/                       # Conexión, sesión, Base y seeds
│   ├── models/                   # Modelos SQLAlchemy (16 tablas)
│   ├── routers/                  # 14 routers HTTP
│   ├── schemas/                  # DTOs Pydantic
│   ├── services/                 # Lógica de negocio e integraciones
│   └── automations/              # Esqueletos de automatizaciones (vacíos)
├── alembic/
│   └── versions/                 # 3 migraciones Python (no hay alembic.ini/env.py)
├── supabase/
│   ├── config.toml               # Configuración local de Supabase CLI
│   └── migrations/               # 7 migraciones SQL (esquema real de la base)
├── tests/                        # Suite de pytest
├── docs/                         # Documentación y capturas
├── requirements.txt              # Dependencias Python
├── .env                          # Variables de entorno (gitignored)
├── .gitignore
├── Dockerfile                    # VACÍO (0 líneas)
└── docker-compose.yml            # VACÍO (0 líneas)
```

## `app/`

### `app/main.py`

- Factory `create_app()` que instancia `FastAPI(title="Turnogo")`.
- Registra `CORSMiddleware` (orígenes `localhost:5173`, `www.turnogo.app`, `turnogo.app`).
- Endpoints de raíz: `GET /` (healthcheck) y `GET /db-test` (prueba de conexión).
- Importa y monta los 13 routers con prefijo `/api`.

### `app/core/`

| Archivo | Contenido |
|---|---|
| `config.py` | Variables de entorno con `python-decouple`: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `TWO_FACTOR_TOKEN_EXPIRE_HOURS`, `RESEND_API_KEY`, `FRONTEND_URL`, `BACKEND_URL`, `MAPBOX_ACCESS_TOKEN`, `MERCADOPAGO_ACCESS_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`. |
| `security.py` | Hash bcrypt (`get_password_hash`/`verify_password`) y generación de JWT (`create_access_token`, HS256). |
| `dependencies.py` | `get_db`, `get_current_user`, `get_current_negocio`, `require_feature`. |
| `estados_turno.py` | Constantes de estados y máquina de transiciones permitidas (`TRANSICIONES_PERMITIDAS`). |
| `roles.py` | Roles `admin` y `duenio`. |
| `geocoding.py` | Helper que delega en `mapbox_service.obtener_coordenadas`. |
| `scheduler_wsp.py` | Scheduler APScheduler para recordatorios; **no registrado** en `main.py` (docstring lo indica). |

### `app/db/`

| Archivo | Contenido |
|---|---|
| `base.py` | `Base = declarative_base()` (base común de los modelos). |
| `database.py` | `engine` con pool (`pool_size=5`, `max_overflow=10`, `pool_recycle=300`, `pool_pre_ping`) y `SessionLocal`; `DATABASE_URL` desde `config('DB')`. |
| `session.py` | `get_db()` (generador de sesión; duplicado de `core/dependencies.get_db`). |
| `seeds/seed_planes.py` | Carga planes Free / Básico / VIP con sus `feature_keys`. |
| `seeds/seed_provincias.py` | Carga las 24 provincias argentinas. |

### `app/models/`

Modelos SQLAlchemy (uno por archivo):

`usuario.py`, `negocio.py`, `turnos.py`, `servicio.py`, `empleado.py`, `cliente.py`, `estado_turno.py`, `horarios_negocio.py`, `categoria.py`, `negocio_imagen.py`, `localidad.py`, `provincia.py`, `plan.py`, `plan_feature.py`, `suscripcion.py`, `metodo_pago.py`.

Detalles verificables:

- `Negocio.usuario_id` es **UNIQUE** → un usuario solo puede tener un negocio.
- `Negocio` expone relaciones `turnos`, `servicios`, `empleados`, `horarios`, `imagenes`, `suscripciones` con `cascade="all, delete-orphan"`.
- `Turno` referencia `id_negocio`, `id_servicio`, `id_empleado`, `id_cliente`, `id_estado`, con `fecha_hora_inicio/fin`, `rechazado_motivo` y `recordatorio_enviado`.
- `Plan.feature_keys` es una property que devuelve los `feature_key` de sus `PlanFeature`.

### `app/routers/`

14 routers: `auth_router`, `turno_router`, `negocio_router`, `servicio_router`, `empleado_router`, `cliente_router`, `horarios_negocio_router`, `categoria_router`, `georef_router`, `plan_router`, `pago_router`, `estadistica`, `usuario_router` y `admin_router`.

- `admin_router.py` contiene **solo código comentado** (un endpoint de dashboard administrativo deshabilitado); no aporta endpoints funcionales.
- Los routers definen `response_model` con los schemas de salida y `status_code` explícito donde corresponde (p. ej. `POST /api/turnos` → 201).

### `app/schemas/`

DTOs Pydantic por dominio:

`auth_schema.py`, `usuario_schema.py`, `negocio_schema.py`, `servicio_schema.py`, `empleado_schema.py`, `cliente_schema.py`, `horarios_negocio_schema.py`, `categoria_schema.py`, `georef_schema.py`, `plan_schema.py`, `appointment_schema.py`, `turno_estado_schema.py` y `estadistica.py`.

- `appointment_schema.py` es el schema central de turnos: `TurnoCrear`, `TurnoActualizar`, `CambiarEstadoTurno` (requiere motivo al cancelar) y `TurnoResponse` anidado.
- `estadistica.py` tipa todas las métricas del dashboard (`Kpis`, `Resumen`, `Clientes`, `Servicios`, `Ingresos`, `Agenda`, `Asistencia`, `EmployeeStatItem`).

### `app/services/`

| Archivo | Rol |
|---|---|
| `auth_service.py` | Registro, login, 2FA OTP, reset/verify, Google OAuth, `/me`. |
| `usuario_service.py` | CRUD de usuarios + verificación de email al crear. |
| `negocio_service.py` | Creación atómica de negocio, slug, geocoding, soft-delete, listados públicos/admin/mapa, backfill. |
| `turno_service.py` | Agenda: crear/actualizar/borrar/cambiar estado con validaciones y emails. |
| `servicio_service.py` | CRUD de servicios + toggle de activo. |
| `empleado_service.py` | Listar/crear empleados con límite por plan (3 en Free). |
| `cliente_service.py` | Normalización de teléfono y patrón get-or-create. |
| `horarios_negocio_service.py` | Gestión de franjas horarias con validación de solapamiento. |
| `categoria_service.py` | CRUD de categorías con validación de URL de icono. |
| `georef_service.py` | Provincias y localidades desde tablas propias. |
| `mapbox_service.py` | Geocoding vía Mapbox (AR). |
| `plan_service.py` | `negocio_tiene_funcion`, `obtener_funciones_negocio`, `obtener_suscripcion_activa`. |
| `payment_service.py` | Preferencias y webhook de MercadoPago, gestión de suscripciones. |
| `estadistica_service.py` | Clase `StatisticsService` con los KPIs del dashboard. |
| `email_service.py` | 6 envíos de email con Resend (verificación, reset, OTP, confirmación con QR, cancelación). |
| `qr_service.py` | `generar_qr_url` (apunta a `FRONTEND_URL/dashboard/turnos?turno={id}`) y `generar_qr_png_bytes`. |
| `whatsapp_service.py`, `dashboard_service.py` | **Vacíos** (0 líneas). |

### `app/automations/`

`reminder_jobs.py`, `daily_closure.py`, `whatsapp_service.py` → **vacíos** (0 líneas). Sin implementación.

## `alembic/versions/`

Migraciones Python:

1. `20260622173000_update_categorias_visual_fields.py` — amplía `icono` a 500 chars y agrega `descripcion`.
2. `20260723000000_add_google_auth.py` — `contrasena_us` nullable + columna `auth_provider`.
3. `20260727000000_add_last_2fa_verified_at.py` — agrega `last_2fa_verified_at`.

No existe `alembic.ini` ni `alembic/env.py` en el repositorio.

## `supabase/`

- `config.toml` — configuración local de la CLI de Supabase (proyecto `TurnoGo`, Postgres 17, puertos locales de Studio/API/DB, Auth local).
- `migrations/` — 7 scripts SQL que describen el **esquema real** de la base:
  - `20260317191220_esquema_inicial_turnexo.sql`
  - `20260317194137_esquema_inicial_turnexo.sql` (contiene el índice GiST `ex_turno_no_solapa_por_empleado`)
  - `20260318221419_remote_schema.sql`
  - `20260318222945_remote_schema.sql`
  - `20260615120000_add_negocio_imagenes.sql`
  - `20260622173000_update_categorias_visual_fields.sql`
  - `20260723000000_add_google_auth.sql`

## `tests/`

Suite con pytest + `TestClient` + SQLite en memoria (`sqlite://` con `StaticPool`):

- `conftest.py` — fixtures `db`, `client`, `setup_db`, `seed_data`; sobrescribe `get_db` de `core.dependencies` y `db.session`.
- `auth_helpers.py` — `obtener_token(client, email, password)`.
- `test_*.py` — cobertura por dominio: auth (service y router), usuarios, negocios, turnos, disponibilidad, categorías, planes, límites de plan, pagos, membresías y estadísticas.

## `docs/`

- `CHANGELOG.md` — historial de limpieza/refactor (cambios de nombres de proyecto, dependencias, tests).
- `screenshot/` — capturas del dashboard y creación de negocio.
- `Test autenticacion.docx` — planilla manual de pruebas de autenticación.
- Documentos de documentación técnica generados: `README.md`, `ARQUITECTURA.md`, `ESTRUCTURA.md`, `TECNOLOGIAS.md`.

## Archivos de configuración y despliegue

| Archivo | Estado verificado |
|---|---|
| `requirements.txt` | Lista de dependencias (todas `>=` salvo `mercadopago==3.3.0` y las secciones de dev). |
| `.env` | Guarda variables usadas por `core/config.py` (gitignored). |
| `Dockerfile` | **Vacío** (0 líneas). |
| `docker-compose.yml` | **Vacío** (0 líneas). |
| `.gitignore` | Excluye `.env`, `venv/`, `*.db`, `htmlcov/`, `.coverage`, `.pytest_cache/`, `.agents/`. |