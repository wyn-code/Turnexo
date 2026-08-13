# API REST — Backend TurnoGo

Guía general de la API REST del backend, con las convenciones de autenticación, errores y el catálogo completo de endpoints organizado por dominio funcional.

> Referencia exhaustiva endpoint por endpoint: [ENDPOINTS.md](./ENDPOINTS.md).

## 1. Base

- **Rutas base:** `/api/<dominio>` (todos los routers se montan con `prefix="/api"` en `app/main.py`).
- **Representación:** JSON.
- **Validación:** Pydantic (cuerpos de entrada y `response_model` de salida).
- **Documentación interactiva (OpenAPI/Swagger):** disponible automáticamente por FastAPI (`/docs`), generada desde los routers y schemas.

## 2. Autenticación

- En los endpoints protegidos el cliente envía el JWT como Bearer token:
  `Authorization: Bearer <access_token>`
- El token se obtiene en `POST /api/auth/login` (o `/verify-2fa`, `/auth/google`, `/verify-email`, `/auth/verify-credentials` según el flujo).
- Dependencias de protección verificadas en el código:
  - `get_current_user` → valida el JWT y devuelve el `Usuario` autenticado.
  - `get_current_negocio` → devuelve el negocio del usuario autenticado (404 si no tiene ninguno).
  - comparación de propiedad en línea (p. ej. `servicio.negocio.usuario_id != current_user.id_us` → 403).

Los endpoints que **no** declaran dependencias de autenticación quedan documentados como "sin autenticación" (ver catálogo).

## 3. Códigos HTTP utilizados

| Código | Uso |
|---|---|
| `200 OK` | Respuestas correctas de GET/POST/PUT/PATCH. |
| `201 Created` | `POST /api/turnos/` y `POST /api/negocios/`. |
| `204 No Content` | `DELETE /api/turnos/{turno_id}` y `DELETE /api/negocios/{negocio_id}`. |
| `400 Bad Request` | Validación de negocio fallida (rango de horario, motivo faltante, categoría inválida…). |
| `401 Unauthorized` | Credenciales/token inválidos o código OTP erróneo/expirado. |
| `403 Forbidden` | Verificación de email pendiente, sin suscripción de la feature pedida, o quien no es dueño intenta operar. |
| `404 Not Found` | Recurso inexistente o sin negocio registrado. |
| `409 Conflict` | Duplicados (usuario/email/categoría) y solapamiento de turnos (restricción GiST). |
| `500 Internal Server Error` | Errores no controlados del servicio. |
| `502 Bad Gateway` | Error al comunicarse con MercadoPago. |

## 4. Formato de errores

FastAPI devuelve el cuerpo:

```json
{ "detail": "<mensaje>" }
```

Los mensajes provienen de `HTTPException(status_code, detail=...)` levantadas en routers y services. Los mensajes exactos se listan por endpoint en [ENDPOINTS.md](./ENDPOINTS.md).

Excepciones conocidas a ese formato:
- `DELETE /api/turnos/{turno_id}` y `DELETE /api/negocios/{negocio_id}` → `204` sin cuerpo; algunos paths devuelven dicts con `{"mensaje": ...}` (p. ej. eliminar categoría/empleado de usuario).

## 5. Organización por dominio funcional

Los dominios reales verificados en `app/routers/` son:

| # | Dominio | Router | Prefijo |
|---|---|---|---|
| 1 | Healthcheck | `app/main.py` | `/` |
| 2 | Autenticación | `auth_router.py` | `/api/auth` |
| 3 | Usuarios | `usuario_router.py` | `/api/usuarios` |
| 4 | Negocios | `negocio_router.py` | `/api/negocios` |
| 5 | Servicios | `servicio_router.py` | `/api/servicios` |
| 6 | Empleados | `empleado_router.py` | `/api/empleados` |
| 7 | Clientes | `cliente_router.py` | `/api/clientes` |
| 8 | Horarios | `horarios_negocio_router.py` | `/api/horarios` |
| 9 | Turnos | `turno_router.py` | `/api/turnos` |
| 10 | Categorías | `categoria_router.py` | `/api/categorias` |
| 11 | Georef | `georef_router.py` | `/api/georef` |
| 12 | Planes | `plan_router.py` | `/api/planes` |
| 13 | Pagos y suscripciones | `pago_router.py` | `/api/pagos` |
| 14 | Estadísticas | `estadistica.py` | `/api/statistics` |

> No existe router dedicado de **QR** ni de **suscripciones** como recurso propio: el QR se genera en el email de confirmación de turno (`qr_service.py`, ver dominio Turnos) y las suscripciones se gestionan dentro de `pago_router.py`.

### 5.1 Resumen de todos los endpoints

#### Healthcheck (`app/main.py`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/` | — |
| GET | `/db-test` | — |

#### Autenticación (`/api/auth`)

| Método | Ruta | Auth |
|---|---|---|
| POST | `/api/auth/register` | — |
| POST | `/api/auth/login` | — |
| POST | `/api/auth/google` | — |
| GET | `/api/auth/me` | Sí (`get_current_user`) |
| GET | `/api/auth/test-email` | — |
| POST | `/api/auth/forgot-password` | — |
| POST | `/api/auth/reset-password/{token}` | — |
| GET | `/api/auth/verify-email/{token}` | — |
| POST | `/api/auth/verify-credentials` | — |
| POST | `/api/auth/verify-2fa` | — |
| POST | `/api/auth/resend-code` | — |

#### Usuarios (`/api/usuarios`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/usuarios/` | — |
| GET | `/api/usuarios/admin` | — |
| GET | `/api/usuarios/{usuario_id}` | — |
| POST | `/api/usuarios/` | — |
| PUT | `/api/usuarios/{usuario_id}` | — |
| PATCH | `/api/usuarios/{usuario_id}/estado` | — |
| DELETE | `/api/usuarios/{usuario_id}` | — |

#### Negocios (`/api/negocios`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/negocios/` | — |
| GET | `/api/negocios/mapa` | — |
| GET | `/api/negocios/admin` | — |
| GET | `/api/negocios/me` | Sí |
| GET | `/api/negocios/slug/{slug}` | — |
| GET | `/api/negocios/{negocio_id}` | — |
| POST | `/api/negocios/` | Sí |
| POST | `/api/negocios/complete` (oculto de OpenAPI) | Sí |
| PUT | `/api/negocios/{negocio_id}` | Sí |
| DELETE | `/api/negocios/{negocio_id}` | Sí |
| POST | `/api/negocios/admin/rebuild-data` | — |
| POST | `/api/negocios/backfill-coordenadas` | — |

#### Servicios (`/api/servicios`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/servicios/` | — |
| POST | `/api/servicios/` | Sí + propiedad |
| PUT | `/api/servicios/{id_servicio}` | Sí + propiedad |
| PATCH | `/api/servicios/{id_servicio}` | Sí + propiedad |
| DELETE | `/api/servicios/{id_servicio}` | Sí + propiedad |

#### Empleados (`/api/empleados`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/empleados/` | — |
| GET | `/api/empleados/{empleado_id}` | — |
| POST | `/api/empleados/` | — |

#### Clientes (`/api/clientes`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/clientes/` | — |
| GET | `/api/clientes/{cliente_id}` | — |
| POST | `/api/clientes/get-or-create` | — |

#### Horarios (`/api/horarios`)

| Método | Ruta | Auth |
|---|---|---|
| POST | `/api/horarios/{id_negocio}` | — |
| GET | `/api/horarios/{id_negocio}` | — |
| PUT | `/api/horarios/{id_negocio}` | — |
| DELETE | `/api/horarios/{id_negocio}` | — |

#### Turnos (`/api/turnos`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/turnos/por-rango` | — |
| GET | `/api/turnos/` | — |
| GET | `/api/turnos/{turno_id}` | — |
| POST | `/api/turnos/` | — |
| PUT | `/api/turnos/{turno_id}` | — |
| PUT | `/api/turnos/{turno_id}/estado` | Sí (`get_current_negocio`) |
| DELETE | `/api/turnos/{turno_id}` | — |

#### Categorías (`/api/categorias`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/categorias/` | — |
| GET | `/api/categorias/{categoria_id}` | — |
| POST | `/api/categorias/` | — |
| PUT | `/api/categorias/{categoria_id}` | — |
| DELETE | `/api/categorias/{categoria_id}` | — |

#### Georef (`/api/georef`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/georef/provincias` | — |
| GET | `/api/georef/localidades` | — |
| GET | `/api/georef/test-geocoding` | — |

#### Planes (`/api/planes`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/planes/` | — |
| GET | `/api/planes/negocios/{id_negocio}/funciones` | — |

#### Pagos y suscripciones (`/api/pagos`)

| Método | Ruta | Auth |
|---|---|---|
| POST | `/api/pagos/crear-preferencia` | Sí (`get_current_negocio`) |
| POST | `/api/pagos/webhook` | — (sin firma verificada en el código) |
| GET | `/api/pagos/suscripcion/actual` | Sí |
| POST | `/api/pagos/suscripcion/{id_suscripcion}/cancelar` | Sí |
| PUT | `/api/pagos/suscripcion/{id_suscripcion}/renovacion-automatica` | Sí |

#### Estadísticas (`/api/statistics`)

| Método | Ruta | Auth |
|---|---|---|
| GET | `/api/statistics/business/{business_id}` | Sí (`get_current_negocio`) |

### 5.2 Detalle por endpoint

Cada endpoint con su método exacto, parámetros, body/schema, respuestas, códigos y errores posibles se documenta en [ENDPOINTS.md](./ENDPOINTS.md), en el mismo orden de dominios.