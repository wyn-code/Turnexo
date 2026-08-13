# AUTORIZACIÓN — Análisis de roles y matrices de acceso del backend Turnogo

> Alcance: los 14 routers montados en `app/main.py:48-60` y las dependencias de `app/core/dependencies.py`.
> Convenciones: `🔒` = requiere token (por defecto `get_current_user`); `🌐` = público (solo `get_db`); `role` = campo `Usuario.role`.
> Estado por ítem: `IMPLEMENTADO` / `NO IMPLEMENTADO` / `NO DETERMINADO`.

---

## 1. Resumen ejecutivo

| Concepto | Estado |
|---|---|
| Modelo de roles (campo `role` con default `"duenio"`) | IMPLEMENTADO (modelo) |
| Uso real del `role` para decidir permisos | NO IMPLEMENTADO |
| Protección por autenticación en **algunos** endpoints | IMPLEMENTADO |
| Protección de escritura/lectura de datos sensibles | PARCIAL (usuarios y turnos protegidos; otros routers siguen públicos) |
| Control de propiedad (`ownership`/IDOR) de recursos | NO IMPLEMENTADO |
| Panel/admin independiente | NO IMPLEMENTADO (`admin_router.py` es solo docstring) |
| Gating por plan (`require_feature`) | IMPLEMENTADO (aplica donde se lo inyecte) |

**Conclusión:** no existe una política de autorización. El `role` se almacena pero nunca se consulta para decidir acceso; la protección se reduce a exigir un usuario autenticado en unos pocos endpoints, y aun así **sin verificar que el recurso le pertenezca** al usuario que lo pide.

---

## 2. Modelo de roles (campo en BD)

- `IMPLEMENTADO` `Usuario.role` columna `String(20)` con default `"duenio"`. `app/models/usuario.py:42-45`.
- `IMPLEMENTADO` `/auth/me` devuelve `role` en la respuesta. `auth_service.py:155-163`.
- `NO IMPLEMENTADO` No se encontró **ninguna** condición que compare `current_user.role` con un recurso o acción. El rol no protege nada.
- `NO DETERMINADO` Valores posibles del rol (¿`duenio`, `admin`, `empleado`, `cliente`, `staff`?). Solo el default `"duenio"` está en el código.

Dependencias disponibles:
- `get_current_user` → valida el JWT y devuelve el `Usuario`. `dependencies.py`.
- `get_current_negocio` → devuelve el negocio del usuario autenticado o 404. `dependencies.py`.
- `require_feature(feature_key)` → 403 si el plan no incluye la función. `dependencies.py` (definida; ver §7).

---

## 3. Matriz de acceso (verificada endpoint por endpoint)

| Router (prefijo) | Endpoints | Acceso | Evidencia |
|---|---|---|---|
| `/auth` | register, login, google, verify-credentials, verify-2fa, resend-code, forgot-password, reset-password, verify-email, **test-email** | 🌐 públicos | `auth_router.py` |
| `/auth` | **GET /me** | 🔒 `get_current_user` | `auth_router.py:72-77` |
| `/usuarios` | GET /, GET /admin, GET /{id}, POST /, PUT /{id}, PATCH /{id}/estado, DELETE /{id} | 🔒 todos (`get_current_user`) | `usuario_router.py` |
| `/negocios` | POST /admin/rebuild-data, GET /mapa, GET /, GET /admin, GET /slug/{slug}, GET /{id}, POST /backfill-coordenadas | 🌐 públicos | `negocio_router.py:19-36,77-90,117-121` |
| `/negocios` | GET /me, POST /, POST /complete, PUT /{id}, DELETE /{id} | 🔒 | `negocio_router.py:38-74,93-114` |
| `/turnos` | GET /por-rango, POST / | 🌐 públicos (booking público) | `turno_router.py` |
| `/turnos` | GET /, GET /{id}, PUT /{id}, DELETE /{id}, PUT /{id}/estado | 🔒 `get_current_negocio` + verificación de propiedad del negocio | `turno_router.py` |
| `/clientes` | GET/POST, GET/{id} | 🌐 públicos | `cliente_router.py` |
| `/empleados` | GET/POST, GET/{id} | 🌐 públicos | `empleado_router.py` |
| `/servicios` | CRUD completo | 🌐 públicos | `servicio_router.py` |
| `/categorias` | CRUD completo | 🌐 públicos | `categoria_router.py` |
| `/horarios` | CRUD completo | 🌐 públicos | `horarios_negocio_router.py` |
| `/georef` | consultas | 🌐 públicos | `georef_router.py` |
| `/planes` | listado/consulta | 🌐 públicos | `plan_router.py` |
| `/estadistica` | una ruta principal | 🔒 `get_current_negocio` | `estadistica.py:26-27` |
| `/pagos` | POST /webhook | 🌐 público (sin firma, ver SEGURIDAD.md) | `pago_router.py:39-65` |
| `/pagos` | crear-preferencia, suscripcion/actual, cancelar, renovacion-automatica | 🔒 `get_current_negocio` | `pago_router.py:23-36,68-93` |

> Nota de exactitud: `/estadistica` y otros routers de solo lectura no listados con `porte` individual fueron relevados por dependencias (grep de `Depends`). Los **suplentes** (p. ej. `get_db` importado de `app.db.session` en `usuario_router.py:4`) son equivalentes.

---

## 4. Hallazgos críticos

### 4.1 `usuario_router` completamente público — CORREGIDO (12/08/2026)
- **Estado:** todos los endpoints de `/api/usuarios` ahora exigen `get_current_user` (autenticación). Se eliminó el acceso anónimo a creación, borrado, cambio de estado y al listado `/admin`.
- **Pendiente:** restringir `/admin` y las mutaciones a `role="admin"` cuando exista gestión de roles (los schemas `UsuarioCreate`/`UsuarioUpdate` no permiten setear `role`, así que no hay escalación por API). `usuario_router.py`.

### 4.2 `turno_router` con CRUD público — CORREGIDO (12/08/2026)
- **Estado:** `GET /`, `GET /{id}`, `PUT /{id}` y `DELETE /{id}` ahora exigen `get_current_negocio` y **verifican que el turno pertenezca al negocio del token** (404 si no coincide). `turno_router.py` + `turno_service.py`.
- **Por diseño (booking público):** `GET /por-rango` (disponibilidad) y `POST /` (crear reserva) permanecen públicos porque `/reservar/:slug` del frontend los usa sin login (`appointment.service.ts`, `Reservar.tsx`). `GET /` ya no expone la agenda de todos los negocios.

### 4.3 `negocio_router`: endpoints de mantenimiento y admin públicos — ALTO
- `POST /admin/rebuild-data` y `POST /backfill-coordenadas` ejecutan backfill de datos sin token. `negocio_router.py:19-21,117-121`.
- `GET /admin` (`listar_negocios_admin`) público → listado administrativo (probablemente con datos internos). `negocio_router.py:34-36`.

### 4.4 `admin_router.py` no existe como endpoint — NO IMPLEMENTADO
- El archivo completo es un **docstring** con un diseño propuesto (incluye el texto de un ejemplo de `get_current_user`). No se monta en `main.py`. No hay panel de administración real. `admin_router.py`.

### 4.5 Sin verificación de propiedad (IDOR) — PARCIAL
- **Corregido en turnos:** `actualizar_turno`, `borrar_turno`, `obtener_turno_por_id` y `listar_turnos` reciben `id_negocio` y validan pertenencia (404). `turno_service.py`.
- **Pendiente en negocios:** `PUT /negocios/{id}` / `DELETE /negocios/{id}` (`negocio_router.py:93-114`): la protección depende de `negocio_service.actualizar_negocio/eliminar_negocio` — NO DETERMINADO si validan que el `negocio_id` pertenece a `current_user`.

### 4.6 `test-email` expuesto — MEDIO
- `GET /auth/test-email` envía un email de verificación a `brunoo6.massocco@gmail.com` (hardcodeado) sin autenticación. Debe eliminarse en producción. `auth_router.py:79-89`.

---

## 5. Qué SÍ está protegido (y la brecha que queda)

- 🔒 `GET /auth/me` (`auth_router.py:72`)
- 🔒 CRUD de `/negocios` de escritura (`negocio_router.py`)
- 🔒 `/usuarios` completo (todos los endpoints, `usuario_router.py`)
- 🔒 `/turnos`: GET /, GET /{id}, PUT /{id}, DELETE /{id}, PUT /{id}/estado (con verificación de propiedad)
- 🔒 Pagos de suscripción (crear preferencia, cancelar, renovar, ver actual)
- 🔒 Ruta principal de `/estadistica`

**Brecha restante:** siguen públicos los routers `/clientes`, `/empleados`, `/servicios`, `/categorias`, `/horarios` y `/planes` (lectura/escritura sin token) y los endpoints de mantenimiento de `/negocios` (`/admin/rebuild-data`, `/backfill-coordenadas`, `/admin`). `GET /turnos/por-rango` y `POST /turnos/` son públicos por diseño (booking público), pero `por-rango` expone datos del cliente en la respuesta.

---

## 6. Roles vs. negocio: el modelo no coincide con la operación

- El modelo define `Usuario.role` y `Negocio.usuario_id` (un negocio por usuario). `usuario.py:122-127`.
- `get_current_negocio` asocia token → negocio, pero **no** distingue si el llamante es el dueño, un `empleado` con permisos parciales o un `staff`.
- `require_feature` autoriza **por plan del negocio**, no por rol del usuario.

---

## 7. `require_feature` (gating por plan)

- `IMPLEMENTADO` `require_feature(feature_key)` devuelve 403 "Tu plan actual no incluye..." cuando el negocio no tiene la función en su plan. Se apoya en `plan_service.negocio_tiene_funcion`. `dependencies.py`.
- `NO DETERMINADO` En qué endpoints se inyecta actualmente (no se halló `Depends(require_feature(...))` en el relevamiento de dependencias).
- Es el único mecanismo de autorización "funcional" del sistema, y es por suscripción, no por rol.

---

## 8. Recomendaciones

1. **Dependencia global de autenticación** en lugar de por-endpoint: `app = FastAPI(dependencies=[Depends(get_current_user)])` y abrir solo rutas públicas explícitas.
2. **RBAC mínimo**: definir enum de roles (`duenio`, `empleado`, `admin`, `cliente`), crear dependencia `require_role(...)` y aplicarla en los routers de escritura.
3. **Cerrar `usuario_router`**: mover `/admin` bajo `require_role("admin")`; exigir token en POST/PUT/PATCH/DELETE; prohibir setear `role` vía API pública.
4. **Cerrar `turno_router`**: exigir `get_current_negocio` y validar que el turno pertenezca al negocio del token.
5. **Ownership obligatorio**: en toda mutación por `{id}` validar `Negocio.usuario_id == current_user.id_us` (o cliente asociado).
6. Eliminar endpoints de mantenimiento (`/admin/rebuild-data`, `/backfill-coordenadas`, `/test-email`, `/auth/test-email`) o protegerlos con `require_role("superadmin")`.
7. Definir si `GET /` catálogo (negocios/servicios/planes) es público por diseño y documentarlo explícitamente.