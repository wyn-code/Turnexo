# Changelog — Turnogo

## Limpieza general

### Fase 1 — Repositorio
- **1.2** — Agregado `*.db` al `.gitignore` y eliminados `test.db` (raíz + `app/`)
- **1.4** — Renombrado `tests/auth.py` → `tests/auth_helpers.py` (no seguía convención `test_*.py`)
- Eliminada carpeta `htmlcov/` (reporte de coverage autogenerado)
- Movidos 5 archivos `.txt`/`.docx` de la raíz a `docs/`
- Eliminado `requirements.txt` duplicado en la raíz del proyecto

### Fase 3 — Código
- **3.1** — Eliminado endpoint `/test` duplicado en `main.py`
- **3.2** — Renombrado proyecto: `Turnexo` → `Turnogo` en `main.py`, `email_service.py`, `turno_service.py`
- Eliminados endpoints `/categorias` (mock hardcodeado) y `/test` (redundante) de `main.py`
- Corregido import: `import sqlalchemy` → `from sqlalchemy import text`
- Agregados `tags` faltantes en routers: Auth, Servicios, Negocios

### Fase 4 — Tests
- Corregido import desactualizado `from .auth` → `from tests.auth_helpers` en 5 archivos
- Corregido payload del test `test_owner_no_puede_crear_servicio_en_negocio_ajeno` (campos incorrectos)
- Eliminado test `test_owner_no_puede_acceder_dashboard_privado_ajeno` (endpoint inexistente)
- **70 tests pasando, 0 fallos**

### Fase 5 — Dependencias
- Versiones relajadas: `==` → `>=` en `requirements.txt`
- Eliminado `uvloop` (no compatible con Windows)
- Agregado `pylint` como dependencia de desarrollo

### Otros
- `htmlcov/`, `.coverage`, `.pytest_cache/`, `.agents/` agregados al `.gitignore`
- README actualizado: título "Turnogo", PostgreSQL (Supabase) en vez de SQL Server
- Eliminados ~20 `print()` de debug en services, routers y database
- Actualizado `database.py` para silenciar prints de conexión

### Fase 6 — Seguridad (hallazgos críticos)
- **CRÍTICO 1** — `usuario_router`: todos los endpoints (GET, POST, PUT, PATCH estado, DELETE, `/admin`) ahora exigen `get_current_user`
- **CRÍTICO 2** — `turno_router`: `GET /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}` ahora exigen `get_current_negocio` y verificación de propiedad del negocio en `turno_service`; `por-rango` y `POST /` siguen públicos (booking)
- **CRÍTICO 3** — `config.py`: `SECRET_KEY` sin default inseguro; ahora obligatoria
- **CRÍTICO 4** — Migración `20260812120000_rls_politicas.sql`: políticas RLS de lectura pública para el catálogo; tablas sensibles denegadas a `anon`/`authenticated`
- Docs actualizados: `AUTENTICACION.md`, `AUTORIZACION.md`, `SEGURIDAD.md`, `CONFIGURACION.md`, `DESPLIEGUE.md`
- **122 tests pasando, 0 fallos**
