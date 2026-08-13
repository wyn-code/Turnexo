# Documentación técnica — Backend TurnoGo

Esta carpeta contiene la documentación técnica del backend de **TurnoGo**, el sistema de gestión de turnos. Todos los documentos describen exclusivamente lo que puede verificarse en el código fuente del repositorio (`app/`, `alembic/`, `supabase/`, `tests/`).

## Índice de documentación

| Documento | Contenido |
|---|---|
| [README.md](./README.md) | Este índice. |
| [ARQUITECTURA.md](./ARQUITECTURA.md) | Arquitectura general, capas, flujo de una petición, dependencias, acceso a datos, servicios externos. |
| [ESTRUCTURA.md](./ESTRUCTURA.md) | Carpetas y archivos importantes del repositorio. |
| [TECNOLOGIAS.md](./TECNOLOGIAS.md) | Tecnologías y librerías realmente utilizadas. |
| [API.md](./API.md) | Guía general de la API REST: convenciones, autenticación, códigos HTTP y catálogo por dominio. |
| [ENDPOINTS.md](./ENDPOINTS.md) | Referencia completa endpoint por endpoint (método, ruta, schema, respuestas, códigos y errores). |

## Descripción general

Aplicación web full stack para la gestión de turnos. El backend es una **API REST monolítica modular** construida con **FastAPI** que expone los recursos del dominio (usuarios, negocios, servicios, empleados, clientes, turnos, horarios, planes, suscripciones, pagos y estadísticas) bajo el prefijo `/api`.

El acceso a datos se realiza con **SQLAlchemy ORM** sobre **PostgreSQL 17 alojado en Supabase**. La autenticación es por **JWT (HS256)** con flujo de verificación de email y segundo factor por OTP. El sistema integra servicios externos para emails (**Resend**), pagos (**MercadoPago**), geocodificación (**Mapbox**) e inicio de sesión (**Google OAuth**).

```
┌──────────────────────────┐        ┌───────────────────────────────────────┐
│  Frontend (React + TS)   │  HTTP  │            FastAPI Backend            │
│  http://localhost:5173   │ ─────► │  /api  →  Routers → Services → Models │
│  https://www.turnogo.app │        └───────────┬───────────────────────────┘
└──────────────────────────┘                    │
                                                ▼
                                     PostgreSQL (Supabase)
```

## Cómo generar el árbol de archivos (referencia)

```
$ tree -I "__pycache__|venv|.git|.pytest_cache"
```

## Contexto técnico

- **Punto de entrada:** `app/main.py` (crea la instancia `app` de FastAPI).
- **Configuración:** variables de entorno leídas con `python-decouple` desde `.env` (`app/core/config.py`).
- **Migraciones de base de datos:** SQL crudo en `supabase/migrations/` (esquema real) y migraciones Python en `alembic/versions/`.
- **Pruebas:** `tests/` con pytest + `TestClient` sobre SQLite en memoria.

## Otros documentos del proyecto

- `docs/CHANGELOG.md` — historial de limpieza de código del repositorio.
- Capturas del sistema: `docs/screenshot/`.