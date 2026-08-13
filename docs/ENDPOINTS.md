# Endpoints — Backend TurnoGo

Referencia completa, endpoint por endpoint, de la API real del backend. Verificado directamente en `app/routers/` y `app/main.py`.

**Convenciones de la sección:**
- Todas las rutas están precedidas por `/api` (prefijo de montaje en `app/main.py`).
- **Auth** indica qué dependencia protege el endpoint (`get_current_user`, `get_current_negocio`, o "ninguna").
- Los cuerpos de respuesta reportados son los `response_model` declarados o los dicts que efectivamente devuelve la función.
- Los errores posibles son los que el código levanta explícitamente (mensajes de `HTTPException`).

## Índice

1. [Healthcheck](#1-healthcheck)
2. [Autenticación](#2-autenticacion)
3. [Usuarios](#3-usuarios)
4. [Negocios](#4-negocios)
5. [Servicios](#5-servicios)
6. [Empleados](#6-empleados)
7. [Clientes](#7-clientes)
8. [Horarios](#8-horarios)
9. [Turnos](#9-turnos)
10. [Categorías](#10-categorias)
11. [Georef](#11-georef)
12. [Planes](#12-planes)
13. [Pagos y suscripciones](#13-pagos-y-suscripciones)
14. [Estadísticas](#14-estadisticas)

---

## 1. Healthcheck

Router: `app/main.py` (definidos en la factory `create_app`).

### GET `/`

- **Router:** `app/main.py`
- **Descripción:** Healthcheck de la API.
- **Path / Query / Body:** ninguno.
- **Respuesta (200):**
  ```json
  { "mensaje": "API Turnogo funcionando 🚀" }
  ```
- **Códigos HTTP:** `200`.
- **Autenticación:** ninguna.
- **Errores posibles:** ninguno explícito.

### GET `/db-test`

- **Router:** `app/main.py`
- **Descripción:** Prueba de conexión a la base de datos ejecutando `SELECT 'conexion OK'`.
- **Respuesta (200):**
  ```json
  { "resultado": "conexion OK con postgres" }
  ```
- **Códigos HTTP:** `200`.
- **Autenticación:** ninguna.
- **Errores posibles:** si la conexión falla, excepción no controlada (500).

---

## 2. Autenticación

Router: `app/routers/auth_router.py` → prefijo `/auth`.

### POST `/api/auth/register`

- **Descripción:** Crea una cuenta. Valida duplicados (email o usuario) y complejidad de contraseña, hashea la contraseña, genera token de verificación de 24 h y envía email de verificación (Resend). No devuelve token: la cuenta queda `email_verified=False`.
- **Auth:** ninguna.
- **Body (schema `RegisterRequest`, `app/schemas/auth_schema.py`):**
  ```json
  {
    "usuario_us": "juan123",
    "email_us": "juan@example.com",
    "contrasena_us": "Clave12345@"
  }
  ```
  | Campo | Tipo | Reglas |
  |---|---|---|
  | `usuario_us` | string | 3–30 |
  | `email_us` | email (`EmailStr`) | válido |
  | `contrasena_us` | string | 12–16, con mayúscula, minúscula, número y carácter especial (`PASSWORD_REGEX`) |
- **Respuesta (200, sin `response_model`):**
  ```json
  { "message": "Cuenta creada. Revisá tu email para verificarla.", "email": "juan@example.com" }
  ```
- **Errores:**
  - `409` — `"El email o nombre de usuario ya existe"`.
  - `400` — contraseña que no cumple `PASSWORD_REGEX` ("La contraseña debe tener entre 12 y 16 caracteres…").
  - `422` — validación de schema de Pydantic (campo faltante, email inválido, largo fuera de rango).

### POST `/api/auth/login`

- **Descripción:** Login simple. Verifica credenciales y `email_verified`; devuelve el JWT. (Para el flujo con 2FA se usa `verify-credentials` + `verify-2fa`.)
- **Auth:** ninguna.
- **Body (schema `LoginRequest`):**
  ```json
  { "email_us": "juan@example.com", "contrasena_us": "Clave12345@" }
  ```
  `email_us` acepta email **o** nombre de usuario; `contrasena_us` de 12–16.
- **Respuesta (200, `TokenResponse`):**
  ```json
  { "access_token": "<jwt>", "token_type": "bearer" }
  ```
  Token con `sub = usuario.id_us` y expiración `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).
- **Errores:**
  - `401` — `"Credenciales invalidas"` (usuario o contraseña incorrectos).
  - `403` — `"Debes verificar tu email antes de iniciar sesión"`.
  - `422` — validación de schema.

### POST `/api/auth/google`

- **Descripción:** Login/registro con Google. Verifica el `id_token` con `google_id_token.verify_oauth2_token` usando `GOOGLE_CLIENT_ID`.
  - Si el email ya existe con `auth_provider="google"`: devuelve token.
  - Si el email existe con otro provider: `409`.
  - Si no existe: crea usuario (sin password, `auth_provider="google"`), envía verificación y devuelve mensaje (sin token).
- **Auth:** ninguna.
- **Body (schema `GoogleLoginRequest`):**
  ```json
  { "id_token": "<id_token_de_google>" }
  ```
- **Respuesta:**
  - Usuario existente (status 200, `TokenResponse`):
    ```json
    { "access_token": "<jwt>", "token_type": "bearer" }
    ```
  - Usuario recién creado (dict):
    ```json
    { "message": "Cuenta creada. Revisá tu email para verificarla.", "email": "user@gmail.com" }
    ```
- **Errores:** `401` (`GoogleAuthError` → `str(e)`), `400` (`"No se pudo obtener el email de Google"`), `409` (`"Este email ya está registrado con contraseña…"`).

### GET `/api/auth/me`

- **Descripción:** Devuelve los datos del usuario autenticado y si posee negocio.
- **Auth:** `get_current_user` (Bearer).
- **Respuesta (200, dict de `build_me_response`):**
  ```json
  {
    "id_us": 1,
    "email_us": "juan@example.com",
    "usuario_us": "juan123",
    "has_business": true,
    "negocio_id": 10,
    "negocio_slug": "mi-negocio",
    "role": "duenio"
  }
  ```
- **Errores:** `401` — `"No se pudo validar el token"` (token ausente/malformado/vencido o usuario inexistente).

### GET `/api/auth/test-email`

- **Descripción:** Endpoint de diagnóstico que envía un email de verificación de prueba (a dirección hardcodeada) y devuelve la respuesta de Resend.
- **Auth:** ninguna.
- **Respuesta (200):**
  ```json
  { "ok": true, "response": { ...respuesta de Resend... } }
  ```
- **Errores:** errores de Resend propagados (500).

### POST `/api/auth/forgot-password`

- **Descripción:** Solicita reset de contraseña. Si el email existe, genera `reset_token` (24 h) y envía email. No revela si el email existe (respuesta uniforme).
- **Auth:** ninguna.
- **Body (schema `ForgotPasswordRequest`):** `{ "email_us": "juan@example.com" }`
- **Respuesta (200):**
  ```json
  { "message": "Si el email existe, se enviará un enlace" }
  ```
- **Errores:** ninguno explícito (`send_reset_password_email` atrapa excepciones).

### POST `/api/auth/reset-password/{token}`

- **Descripción:** Cambia la contraseña usando el token de reset. Exige que nueva y confirmación coincidan; valida la misma política de contraseña y que no sea igual a la anterior.
- **Auth:** ninguna.
- **Path:** `token` (string).
- **Body (schema `ResetPasswordRequest`):**
  ```json
  { "new_password": "NuevaClave1@", "confirm_password": "NuevaClave1@" }
  ```
- **Respuesta (200):** `{ "message": "Contraseña actualizada" }`
- **Errores:**
  - `400` — `"Las contraseñas no coinciden"`; `"Token inválido"`; `"Token expirado"`; mensaje de política de contraseña; `"La nueva contraseña no puede ser igual a la anterior"`.

### GET `/api/auth/verify-email/{token}`

- **Descripción:** Confirma el email (`email_verified=True`), limpia el token y **devuelve un access_token** directo.
- **Auth:** ninguna.
- **Path:** `token` (string).
- **Respuesta (200, dict):**
  ```json
  {
    "message": "Email verificado correctamente",
    "access_token": "<jwt>",
    "token_type": "bearer",
    "usuario_id": 1
  }
  ```
- **Errores:** `400` — `"Token inválido"` o `"Token expirado"`.

### POST `/api/auth/verify-credentials`

- **Descripción:** Paso 1 de login con 2FA. Verifica credenciales y `email_verified`.
  - Si el usuario verificó 2FA recientemente (`last_2fa_verified_at` < `TWO_FACTOR_TOKEN_EXPIRE_HOURS`, default 9 h): devuelve token directo.
  - Si no, genera OTP de 6 dígitos (24 h de expiración de `otp_expires_at`), lo guarda y lo envía por email.
- **Auth:** ninguna.
- **Body (schema `LoginRequest`):** idéntico al del `login`.
- **Respuesta (200, dict; no usa `VerifyCredentialsResponse`):**
  - Con 2FA reciente:
    ```json
    { "success": true, "message": "Token emitido", "access_token": "<jwt>" }
    ```
  - OTP enviado:
    ```json
    { "success": true, "message": "Código enviado al correo" }
    ```
- **Errores:** `401` — `"Credenciales inválidas"`; `403` — `"Debes verificar tu email antes de iniciar sesión"`.

### POST `/api/auth/verify-2fa`

- **Descripción:** Paso 2 de login con 2FA. Valida el OTP (y expiración), marca `last_2fa_verified_at` y emite el token.
- **Auth:** ninguna.
- **Body (schema `Verify2FARequest`):**
  ```json
  { "email_us": "juan@example.com", "otp_code": "123456" }
  ```
  `otp_code` de exactamente 6 caracteres.
- **Respuesta (200, `TokenResponse`):**
  ```json
  { "access_token": "<jwt>", "token_type": "bearer" }
  ```
  Token con 9 h de vida (`TWO_FACTOR_TOKEN_EXPIRE_HOURS`).
- **Errores:** `401` — `"Usuario no encontrado"`, `"El código de verificación ha expirado…"`, `"Código incorrecto"`.

### POST `/api/auth/resend-code`

- **Descripción:** Reenvía el OTP de 2FA (misma lógica que `verify-credentials` sin verificar password).
- **Auth:** ninguna.
- **Body (schema `ResendCodeRequest`):** `{ "email_us": "juan@example.com" }`
- **Respuesta (200, dict):** `{ "success": true, "message": "Token emitido", "access_token": "<jwt>" }` (si 2FA reciente) o `{ "success": true, "message": "Código reenviado al correo" }`.
- **Errores:** `401` — `"Usuario no encontrado"`; `403` — `"Debes verificar tu email antes de iniciar sesión"`.

---

## 3. Usuarios

Router: `app/routers/usuario_router.py` → prefijo `/usuarios`.

> **Nota de seguridad verificable:** ninguno de estos endpoints declara autenticación u ownership.

Schemas (`usuario_schema.py`):
- `UsuarioCreate`: `usuario_us`, `email_us` (EmailStr), `contrasena_us`.
- `UsuarioUpdate`: `usuario_us?`, `email_us?`, `contrasena_us?`.
- `UsuarioResponse`: `usuario_us`, `email_us`, `id_us`, `created_at?`, `role`, `estado`.
- `UsuarioAdminResponse`: `id_us`, `usuario_us`, `email_us`, `role_us?`, `habilitado`, `negocio?`, `estado`.
- `EstadoUsuarioRequest`: `estado` (bool).

### GET `/api/usuarios/`

- **Descripción:** Lista todos los usuarios.
- **Respuesta (200, `list[UsuarioResponse]`).**
- **Errores:** ninguno explícito.

### GET `/api/usuarios/admin`

- **Descripción:** Lista usuarios con su negocio (join). Devuelve dicts con `{id_us, usuario_us, email_us, role_us, estado, negocio}`.
- **Respuesta (200, `list[UsuarioAdminResponse]`).**
- **Errores:** ninguno explícito.

### GET `/api/usuarios/{usuario_id}`

- **Path:** `usuario_id` (int).
- **Descripción:** Obtiene un usuario por ID. **404** si no existe.
- **Respuesta (200, `UsuarioResponse`).**
- **Errores:** `404` — `"Usuario no encontrado"`.

### POST `/api/usuarios/`

- **Descripción:** Crea un usuario. Valida duplicados de `usuario_us` y `email_us`, hashea la contraseña, marca `email_verified=False` y envía email de verificación.
- **Body:** `UsuarioCreate`.
- **Respuesta (200, `UsuarioResponse`).**
- **Errores:** `409` — `"El nombre de usuario ya existe"` o `"El email ya existe"`; `422` — schema.

### PUT `/api/usuarios/{usuario_id}`

- **Path:** `usuario_id` (int).
- **Descripción:** Actualiza usuario (nombre/email/contraseña) con deduplicación excluyendo el propio registro. Si no existe → **404**.
- **Body:** `UsuarioUpdate` (todos opcionales).
- **Respuesta (200, `UsuarioResponse`).**
- **Errores:** `404` — `"Usuario no encontrado"`; `409` — duplicado de usuario o email.

### PATCH `/api/usuarios/{usuario_id}/estado`

- **Path:** `usuario_id` (int).
- **Descripción:** Activa/desactiva un usuario (`estado` bool).
- **Body:** `EstadoUsuarioRequest` → `{ "estado": false }`.
- **Respuesta (200, `UsuarioResponse`).**
- **Errores:** `404` — `"Usuario no encontrado"`.

### DELETE `/api/usuarios/{usuario_id}`

- **Path:** `usuario_id` (int).
- **Descripción:** Elimina físicamente el usuario (cascade a su negocio por FK `ondelete=CASCADE`).
- **Respuesta (200, dict):** `{ "mensaje": "Usuario eliminado" }`; **404** si no existe.
- **Errores:** `404` — `"Usuario no encontrado"`.

---

## 4. Negocios

Router: `app/routers/negocio_router.py` → prefijo `/negocios`.

Schemas (`negocio_schema.py`):
- `NegocioCompleteCreate` = `NegocioCreate` (`nombre`, `wsp`, `telefono?`, `direccion`, `ciudad`, `id_categoria`, `id_localidad?`, `id_provincia?`, `ig_url?`, `logo?`, `descripcion=""`, `activo=true`, `usuario_id?`) + `imagenes: list[str]`, `servicios: list[ServicioCreateNested]`, `empleados: list[EmpleadoCreate]`, `horarios: list[HorarioNegocioCreate]`.
- `NegocioUpdate`: todos opcionales (`nombre`, `wsp`, `telefono`, `direccion`, `ciudad`, `ig_url`, `logo`, `descripcion`, `imagenes`, `id_categoria`, `id_localidad`, `id_provincia`, `activo`).
- Respuestas: `NegocioListResponse` (sin `imagenes`), `NegocioResponse` (con `imagenes`), `NegocioCompleteResponse` (agrega `servicios`, `empleados`, `horarios`), `NegocioAdminResponse`, `NegocioMapaResponse`.

### GET `/api/negocios/`

- **Descripción:** Lista negocios activos (`activo == True`).
- **Respuesta (200, `list[NegocioListResponse]`).**
- **Errores:** ninguno explícito.

### GET `/api/negocios/mapa`

- **Descripción:** Negocios con coordenadas cargadas, activos y con suscripción activa que incluye la feature `mapa_ubicacion`. Devuelve `{id_negocio, nombre, latitud, longitud}`.
- **Respuesta (200, `list[NegocioMapaResponse]`).**
- **Errores:** ninguno explícito.

### GET `/api/negocios/admin`

- **Descripción:** Listado administrativo con el dueño (`{id_negocio, nombre, wsp, telefono, direccion, ciudad, ig_url, activo, slug, duenio: {nombre, email}}`).
- **Respuesta (200, `list[NegocioAdminResponse]`).**
- **Errores:** ninguno explícito (sin auth declarada).

### GET `/api/negocios/me`

- **Auth:** `get_current_user`.
- **Descripción:** Devuelve el negocio del usuario autenticado.
- **Respuesta (200, `NegocioResponse`).**
- **Errores:** `404` — `"El usuario no tiene un negocio"`.

### GET `/api/negocios/slug/{slug}`

- **Path:** `slug` (string).
- **Descripción:** Negocio público por slug (activo), con `horarios`, `imagenes` y `tiene_mapa` calculado.
- **Respuesta (200, `NegocioResponse`).**
- **Errores:** `404` — `"Negocio no encontrado"`.

### GET `/api/negocios/{negocio_id}`

- **Path:** `negocio_id` (int).
- **Descripción:** Negocio público por ID (`obtener_negocio_publico_por_id`), 404 si inactivo.
- **Respuesta (200, `NegocioResponse`).**
- **Errores:** `404` — `"Negocio no encontrado"`.

### POST `/api/negocios/`

- **Auth:** `get_current_user`; `data.usuario_id = current_user.id_us` se asigna en el router.
- **Descripción:** Crea el negocio **de forma atómica**: valida usuario, categoría, localidad/provincia; geocodifica con Mapbox (fallo silencioso); genera `slug` único; inserta negocio, imágenes (primera = portada), servicios, empleados y horarios en una transacción; `db.flush()` + `db.commit()`.
- **Body:** `NegocioCompleteCreate`. Requeridos: `nombre`, `id_categoria`, `wsp`, `direccion`, `ciudad`.
  ```json
  {
    "nombre": "Mi Negocio",
    "id_categoria": 1,
    "wsp": "+5491111111111",
    "direccion": "Av. Siempreviva 742",
    "ciudad": "San Nicolás",
    "id_localidad": 5,
    "id_provincia": 1,
    "imagenes": ["https://cdn/logo.png"],
    "servicios": [{ "nombre_servicio": "Corte", "precio": 5000, "duracion_min": 30, "duracion_max": 30 }],
    "empleados": [{ "nombre": "Ana", "apellido": "Gómez" }],
    "horarios": [{ "dia_semana": 1, "hora_apertura": "09:00", "hora_cierre": "18:00" }]
  }
  ```
- **Respuesta (201, `NegocioCompleteResponse`).**
- **Errores:**
  - `400` — `"id_categoria es obligatorio"`; `"usuario_id es obligatorio"`; `"Usuario no válido"`; `"Categoría no válida"`; `"Localidad no válida"` / `"Provincia no válida"`.
  - `500` — `"Error al crear el negocio"`.

### POST `/api/negocios/complete`

- **Descripción:** Igual a `POST /api/negocios/` (delega al mismo handler) pero con `include_in_schema=False` → **no aparece en OpenAPI**.
- **Auth:** `get_current_user`.
- **Respuesta (201, `NegocioCompleteResponse`).** Mismos errores que el anterior.

### PUT `/api/negocios/{negocio_id}`

- **Auth:** `get_current_user`.
- **Path:** `negocio_id` (int).
- **Descripción:** Actualiza el negocio. Solo el dueño o `role == "admin"`. Aplica campos permitidos vía `ALLOWED_FIELDS`; re-geocodifica si cambió dirección/ciudad; si envía `imagenes`, exige la feature `imagenes_personalizadas` (VIP).
- **Body:** `NegocioUpdate` (todos opcionales).
- **Respuesta (200, `NegocioResponse`).**
- **Errores:**
  - `403` — sin permiso; `403` — `"Tu plan actual no incluye imágenes personalizadas. Actualizá al plan VIP."`
  - `404` — `HTTPException(404)` sin detalle.
  - `400` — `"Categoría no válida"`.

### DELETE `/api/negocios/{negocio_id}`

- **Auth:** `get_current_user`; en el service exige `current_user.role == "admin"`.
- **Path:** `negocio_id` (int).
- **Descripción:** **Soft delete** (`activo = False`).
- **Respuesta (204, sin cuerpo).**
- **Errores:** `403` (no admin); `404` sin detalle.

### POST `/api/negocios/admin/rebuild-data`

- **Descripción:** Ejecuta `backfill_negocios` (backfill de coordenadas a todos los negocios sin lat/long). Sin auth declarada.
- **Respuesta (200):** devuelve `None` (respuesta vacía).
- **Errores:** ninguno explícito.

### POST `/api/negocios/backfill-coordenadas`

- **Descripción:** Igual que el anterior pero devuelve mensaje.
- **Respuesta (200):**
  ```json
  { "mensaje": "Coordenadas actualizadas" }
  ```
- **Errores:** ninguno explícito.

---

## 5. Servicios

Router: `app/routers/servicio_router.py` → prefijo `/servicios`.

Schemas (`servicio_schema.py`):
- `ServicioCreate`: `nombre_servicio`, `precio`, `requiere_aprobacion` (`false`), `duracion_min`, `duracion_max`, `activo` (`true`), `id_negocio`.
- `ServicioUpdate`: todos opcionales.
- `ServicioResponse`: base + `id_servicio`, `id_negocio`.

### GET `/api/servicios/`

- **Query:** `id_negocio` (int, opcional; filtra si se envía).
- **Descripción:** Lista servicios (activos e inactivos).
- **Respuesta (200, `list[ServicioResponse]`).**
- **Errores:** ninguno explícito.

### POST `/api/servicios/`

- **Auth:** `get_current_user` + verificación de propiedad en el router (`negocio.usuario_id != current_user.id_us` → 403).
- **Descripción:** Crea un servicio.
- **Body:** `ServicioCreate`.
- **Respuesta (200, `ServicioResponse`).**
- **Errores:** `404` — `"Negocio no encontrado"`; `403` — `"No tienes permisos para agregar servicios a este negocio"`.

### PUT `/api/servicios/{id_servicio}`

- **Auth:** `get_current_user` + propiedad.
- **Path:** `id_servicio` (int).
- **Descripción:** Actualiza campos del servicio (`exclude_unset=True`).
- **Body:** `ServicioUpdate`.
- **Respuesta (200, `ServicioResponse`).**
- **Errores:** `404` — `"Servicio no encontrado"`; `403` — `"No tienes permisos"`.

### PATCH `/api/servicios/{id_servicio}`

- **Auth:** `get_current_user` + propiedad.
- **Path:** `id_servicio` (int).
- **Descripción:** Toggle de `activo` (`True ↔ False`).
- **Body:** ninguno.
- **Respuesta (200, `ServicioResponse`).**
- **Errores:** `404` — `"Servicio no encontrado"`; `403` — `"No tienes permisos"`.

### DELETE `/api/servicios/{id_servicio}`

- **Auth:** `get_current_user` + propiedad.
- **Path:** `id_servicio` (int).
- **Descripción:** **Soft delete** del servicio (`activo = False`).
- **Respuesta (200, `ServicioResponse`).**
- **Errores:** `404` — `"Servicio no encontrado"`; `403` — `"No tienes permisos"`.

---

## 6. Empleados

Router: `app/routers/empleado_router.py` → prefijo `/empleados`.

Schema `EmpleadoCreate`: `nombre`, `apellido`, `telefono?`, `activo` (`true`), `id_negocio`.

### GET `/api/empleados/`

- **Query:** `id_negocio` (int, opcional).
- **Descripción:** Lista empleados (todos o filtrados por negocio).
- **Respuesta (200, `list[EmpleadoResponse]`).**
- **Errores:** ninguno explícito.

### GET `/api/empleados/{empleado_id}`

- **Path:** `empleado_id` (int).
- **Respuesta (200, `EmpleadoResponse`).**
- **Errores:** `404` — `"Empleado no encontrado"`.

### POST `/api/empleados/`

- **Descripción:** Crea un empleado. Valida que el negocio exista; sin feature `empleados_ilimitados` aplica el límite Free de **3 empleados**.
- **Body:** `EmpleadoCreate`.
- **Respuesta (200, `EmpleadoResponse`).**
- **Errores:**
  - `404` — `"Negocio no encontrado"`.
  - `403` — `"El plan Free permite hasta 3 empleados. Actualizá tu plan para sumar más."`
  - `422` — schema (campos requeridos).

---

## 7. Clientes

Router: `app/routers/cliente_router.py` → prefijo `/clientes`.

Schema `ClienteCreate`: `telefono`, `nombre`, `apellido`, `email?`. `ClienteResponse` agrega `id_cliente`, `created_at`.

### GET `/api/clientes/`

- **Descripción:** Lista todos los clientes (consulta directa en el router).
- **Respuesta (200, `list[ClienteResponse]`).**
- **Errores:** ninguno explícito.

### GET `/api/clientes/{cliente_id}`

- **Path:** `cliente_id` (int).
- **Respuesta (200, `ClienteResponse`).**
- **Errores:** `404` — `"Cliente no encontrado"`.

### POST `/api/clientes/get-or-create`

- **Descripción:** Normaliza el teléfono, busca por teléfono único; si existe y no tiene email, lo actualiza; si no, lo crea. `status_code=200` (no 201).
- **Body:** `ClienteCreate`.
- **Respuesta (200, `ClienteResponse`).**
- **Errores:**
  - `400` — `"El teléfono es obligatorio"`; `"El teléfono no es válido"` (menos de 8 dígitos); `"El nombre es obligatorio"`; `"El apellido es obligatorio"`.
  - `422` — schema (el teléfono es `unique`).

---

## 8. Horarios

Router: `app/routers/horarios_negocio_router.py` → prefijo `/horarios`.

Schema `HorarioNegocioCreate`: `dia_semana` (int), `hora_apertura` (time), `hora_cierre` (time).

### POST `/api/horarios/{id_negocio}`

- **Path:** `id_negocio` (int).
- **Descripción:** Crea franjas horarias del negocio. Valida: apertura ≠ cierre, máximo **2 franjas por día** y que no se solapen.
- **Body:** array de `HorarioNegocioCreate`.
  ```json
  [ { "dia_semana": 1, "hora_apertura": "09:00", "hora_cierre": "13:00" } ]
  ```
- **Respuesta (200, dict):** `{ "message": "Horarios guardados correctamente" }`
- **Errores:**
  - `400` — `"La hora de apertura y cierre no pueden ser iguales…"`; `"El día {n} tiene más de 2 franjas horarias"`; `"Las franjas horarias del día {n} se superponen"`.

### GET `/api/horarios/{id_negocio}`

- **Path:** `id_negocio` (int).
- **Respuesta (200):** lista de `HorarioNegocio` (modelo ORM serializado; sin `response_model`).
  ```json
  [ { "id_horarios_negocio": 1, "id_negocio": 1, "dia_semana": 1, "hora_apertura": "09:00", "hora_cierre": "13:00" } ]
  ```
- **Errores:** `404` — `"No se encontraron horarios para este negocio"`.

### PUT `/api/horarios/{id_negocio}`

- **Path:** `id_negocio` (int).
- **Descripción:** Reemplaza todas las franjas del negocio (borra y reinserta) tras validar.
- **Body:** array de `HorarioNegocioCreate`.
- **Respuesta (200, dict):** `{ "message": "Horarios actualizados correctamente" }`
- **Errores:** `404` — `"No existen horarios para actualizar"`; `400` — validaciones de franjas.

### DELETE `/api/horarios/{id_negocio}`

- **Path:** `id_negocio` (int).
- **Descripción:** Elimina todas las franjas del negocio.
- **Respuesta (200, dict):** `{ "message": "Horarios eliminados correctamente" }`
- **Errores:** `404` — `"No existen horarios para eliminar"`.

---

## 9. Turnos

Router: `app/routers/turno_router.py` → prefijo `/turnos`.

Schemas (`appointment_schema.py`):
- `TurnoCrear`: `id_negocio`, `id_cliente`, `id_servicio`, `fecha_hora_inicio` (datetime), `id_empleado?`.
- `TurnoActualizar`: opcionales (`id_negocio`, `id_cliente`, `id_servicio`, `id_estado`, `id_empleado`, `fecha_hora_inicio`, `fecha_hora_fin`, `rechazado_motivo`).
- `CambiarEstadoTurno`: `id_estado`, `rechazado_motivo?` (**obligatorio** si `id_estado == CANCELADO` (4)).
- `TurnoResponse`: `id_turno`, `id_negocio`, `id_estado`, `fecha_hora_inicio`, `fecha_hora_fin?`, `rechazado_motivo?`, `created_at?`, `updated_at?`, `cliente`, `empleado?`, `servicio`, `estado` (objetos anidados).

Estados (`app/core/estados_turno.py`): `1` PENDIENTE, `2` CONFIRMADO, `3` COMPLETADO, `4` CANCELADO, `5` NO_ASISTIO. Transiciones válidas: `1→{2,4}`, `2→{3,4,5}`.

### GET `/api/turnos/por-rango`

- **Query:**
  | Parámetro | Tipo | Requerido |
  |---|---|---|
  | `id_negocio` | int | sí |
  | `desde` | datetime (ISO) | sí |
  | `hasta` | datetime (ISO) | sí |
  | `id_empleado` | int | no |
- **Descripción:** Turnos de un negocio cuyo rango `[inicio, fin)` interseca `[desde, hasta)`, ordenados por inicio.
- **Respuesta (200, `list[TurnoResponse]`).**
- **Errores:** `400` — `"'hasta' debe ser mayor que 'desde'"`.

### GET `/api/turnos/`

- **Descripción:** Lista todos los turnos del sistema.
- **Respuesta (200, `list[TurnoResponse]`).**
- **Errores:** ninguno explícito.

### GET `/api/turnos/{turno_id}`

- **Path:** `turno_id` (int).
- **Respuesta (200, `TurnoResponse`).**
- **Errores:** `404` — `"Turno no encontrado"`.

### POST `/api/turnos/`

- **Descripción:** Crea un turno con validación completa. Flujo (`turno_service.crear_turno`):
  1. servicio activo del negocio,
  2. límite Free (sin feature `turnos_ilimitados`): máximo **10 turnos del día** por negocio (no cuenta CANCELADO),
  3. `fecha_hora_fin` = inicio + `duracion_min` (si no se envía),
  4. rango válido, empleado del negocio,
  5. dentro del horario de atención (soporta cierre que cruza medianoche),
  6. sin solapamiento (Python + constraint GiST),
  7. cliente existente; estado inicial `CONFIRMADO`.
  Al crear, si el cliente tiene email, encola un **email de confirmación con QR** (`BackgroundTasks`).
- **Body:** `TurnoCrear`.
  ```json
  {
    "id_negocio": 1,
    "id_cliente": 5,
    "id_servicio": 2,
    "fecha_hora_inicio": "2026-04-10T15:00:00",
    "id_empleado": 1
  }
  ```
- **Respuesta (201, `TurnoResponse`).**
- **Errores:**
  - `404` — `"Servicio no encontrado para el negocio indicado o negocio inactivo"`; `"El cliente especificado no existe."`
  - `400` — `"Empleado no encontrado para el negocio indicado"`; `"El turno está fuera del horario de atención del negocio"`; `"La fecha_hora_fin debe ser mayor que la fecha_hora_inicio"`; error de integridad genérico.
  - `403` — `"El plan Free permite hasta 10 turnos por día. Actualizá tu plan para agendar más."`
  - `409` — `"El empleado ya tiene un turno en ese horario"` (aplicación o constraint GiST).

### PUT `/api/turnos/{turno_id}`

- **Path:** `turno_id` (int).
- **Descripción:** Actualiza un turno (campos parciales) con las mismas validaciones; recalcula `fecha_hora_fin` si cambió servicio/negocio/inicio; valida transición de estado si se envía `id_estado`; aplica `rechazado_motivo` si se envía.
- **Body:** `TurnoActualizar`.
- **Respuesta (200, `TurnoResponse`).**
- **Errores:** idénticos a POST más `400` — `"No se puede pasar del estado {a} al {b}"`.

### PUT `/api/turnos/{turno_id}/estado`

- **Auth:** `get_current_negocio`.
- **Path:** `turno_id` (int).
- **Descripción:** Cambia el estado de un turno **del propio negocio** (403 si el turno pertenece a otro). Valida la transición por máquina de estados. Si es una cancelación con email y `rechazado_motivo`, encola email de cancelación en background (`send_cancellation_email`).
- **Body:** `CambiarEstadoTurno`.
  ```json
  { "id_estado": 4, "rechazado_motivo": "Cliente pidió cancelar" }
  ```
- **Respuesta (200, `TurnoResponse`).**
- **Errores:**
  - `404` — `"Turno no encontrado"`.
  - `403` — `"Este turno no pertenece a tu negocio"`.
  - `400` — `"No se puede cambiar del estado {a} al estado {b}"`.
  - `422` — `rechazado_motivo` ausente/corto/largo al cancelar (validador de `CambiarEstadoTurno`: mínimo 5, máximo 500 caracteres).

### DELETE `/api/turnos/{turno_id}`

- **Path:** `turno_id` (int).
- **Descripción:** **Borra físicamente** el turno.
- **Respuesta (204, sin cuerpo).**
- **Errores:** `404` — `"Turno no encontrado"`; `500` — `"Error al eliminar el turno: {detalle}"`.

---

## 10. Categorías

Router: `app/routers/categoria_router.py` → prefijo `/categorias`.

Schema `CategoriaCreate`: `nombre` (1–100, requerido), `icono?` (≤500, URL http(s) de imagen válida si viene con esquema), `descripcion?` (≤255). `CategoriaUpdate`: opcionales.

### GET `/api/categorias/`

- **Descripción:** Lista categorías ordenadas por nombre.
- **Respuesta (200, `list[CategoriaResponse]`).**

### GET `/api/categorias/{categoria_id}`

- **Path:** `categoria_id` (int).
- **Respuesta (200, `CategoriaResponse`).**
- **Errores:** `404` — `"Categoria no encontrada"`.

### POST `/api/categorias/`

- **Descripción:** Crea categoría validando nombre e icono.
- **Body:** `CategoriaCreate`.
- **Respuesta (200, `CategoriaResponse`).**
- **Errores:** `400` — `"nombre es obligatorio"`, `"icono debe ser una URL http(s) valida"`, `"icono debe apuntar a una imagen valida"`; `409` — `"Ya existe una categoria con ese nombre"`.

### PUT `/api/categorias/{categoria_id}`

- **Path:** `categoria_id` (int).
- **Body:** `CategoriaUpdate`.
- **Respuesta (200, `CategoriaResponse`).**
- **Errores:** `400`/`409` como en POST; `404` — `"Categoria no encontrada"`.

### DELETE `/api/categorias/{categoria_id}`

- **Path:** `categoria_id` (int).
- **Descripción:** Elimina físicamente la categoría (puede fallar por FK si tiene negocios).
- **Respuesta (200, dict):** `{ "mensaje": "Categoria eliminada" }`; `404` si no existe.
- **Errores:** `404` — `"Categoria no encontrada"`; `500` — violación de FK no controlada.

---

## 11. Georef

Router: `app/routers/georef_router.py` → prefijo `/georef`.

### GET `/api/georef/provincias`

- **Descripción:** Lista provincias (tabla `provincia`) ordenadas alfabéticamente.
- **Respuesta (200):** `[ { "id_provincia": 1, "nombre": "Buenos Aires" }, ... ]`

### GET `/api/georef/localidades`

- **Query:** `id_provincia` (int, requerido).
- **Descripción:** Lista localidades de una provincia (tabla `localidades`).
- **Respuesta (200):** `[ { "id_localidad": 10, "nombre": "San Nicolás" }, ... ]`

### GET `/api/georef/test-geocoding`

- **Descripción:** Endpoint de diagnóstico: geocodifica `"Av. Corrientes 1234, Buenos Aires, Buenos Aires"` con Mapbox.
- **Respuesta (200):** `[<longitud>, <latitud>]` (array de la API de Mapbox) o `null`.

---

## 12. Planes

Router: `app/routers/plan_router.py` → prefijo `/planes`.

Schema `PlanResponse`: `id_plan`, `nombre`, `precio`, `duracion_dias`, `descripcion?`, `activo`, `feature_keys`. `NegocioFuncionesResponse`: `id_negocio`, `plan?`, `estado?`, `fecha_fin?`, `funciones[].`

### GET `/api/planes/`

- **Descripción:** Lista planes activos con sus `feature_keys` (`selectinload(Plan.funciones)`).
- **Respuesta (200, `list[PlanResponse]`).**

### GET `/api/planes/negocios/{id_negocio}/funciones`

- **Path:** `id_negocio` (int).
- **Descripción:** Devuelve el plan/suscripción activa del negocio y la lista de features habilitadas (`obtener_funciones_negocio`).
- **Respuesta (200, `NegocioFuncionesResponse`):**
  ```json
  { "id_negocio": 1, "plan": "VIP", "estado": "activa", "fecha_fin": "2026-05-10T00:00:00", "funciones": ["mapa_ubicacion", "imagenes_personalizadas", "soporte_prioritario"] }
  ```
- **Errores:** `404` — `"Negocio no encontrado"`.

---

## 13. Pagos y suscripciones

Router: `app/routers/pago_router.py` → prefijo `/pagos`.

Schemas (`plan_schema.py`): `CrearPreferenciaRequest` (`id_plan`), `CrearPreferenciaResponse` (`init_point`, `preference_id`), `RenovacionAutomaticaRequest` (`renovacion_automatica`), `SuscripcionResponse` (`id_suscripcion`, `estado`, `fecha_inicio`, `fecha_fin`, `renovacion_automatica`, `plan`).

### POST `/api/pagos/crear-preferencia`

- **Auth:** `get_current_negocio`.
- **Descripción:** Crea una preferencia de pago en MercadoPago para el plan solicitado.
  - Cancela suscripciones `pendiente` previas del negocio.
  - Guarda una `Suscripcion` en `estado="pendiente"` con `external_subscription_id = preference_id`.
  - `external_reference = "{id_negocio}:{id_plan}"`; `back_urls` y `notification_url` apuntan al front/backend.
  - Usa `sandbox_init_point` si el token de MP empieza con `TEST-`.
- **Body:** `CrearPreferenciaRequest` `{ "id_plan": 2 }`.
- **Respuesta (200, `CrearPreferenciaResponse`):**
  ```json
  { "init_point": "https://www.mercadopago.com.ar/checkout/v1/...", "preference_id": "PV1234" }
  ```
- **Errores:**
  - `404` — `"Plan no encontrado o inactivo"`.
  - `502` — `"Error al comunicarse con MercadoPago: {exc}"` / `"Error al crear la preferencia de pago con MercadoPago"` / `"MercadoPago no devolvió una preferencia válida"`.

### POST `/api/pagos/webhook`

- **Descripción:** Webhook de MercadoPago. Consume `form-data` (`topic`, `id`) o `query` params. Si `topic == "payment"`, consulta `sdk.payment().get(id)`; si `status == "approved"`, parsea `external_reference` (`negocio:plan`), llama `procesar_pago_exitoso` (activa la suscripción y cancela las pendientes/activas del mismo negocio).
- **Auth:** ninguna (el código no verifica firma de MercadoPago).
- **Body:** `application/x-www-form-urlencoded` → `{ "topic": "payment", "id": "123456" }` (o query params equivalentes).
- **Respuesta (200):** `{ "status": "ok" }` (los errores de procesamiento se loguean y no se devuelven).
- **Errores:** ninguno explícito; excepciones atrapadas con `logger.exception`.

### GET `/api/pagos/suscripcion/actual`

- **Auth:** `get_current_negocio`.
- **Descripción:** Última suscripción del negocio (cualquier estado, ordenada por `fecha_inicio` desc).
- **Respuesta (200, `SuscripcionResponse | None`).**
- **Errores:** ninguno explícito (puede devolver `null`).

### POST `/api/pagos/suscripcion/{id_suscripcion}/cancelar`

- **Auth:** `get_current_negocio` (asegura que la suscripción pertenezca al negocio).
- **Path:** `id_suscripcion` (int).
- **Descripción:** Cancela la suscripción (`estado = "cancelada"`), solo si está `activa` o `pendiente`.
- **Respuesta (200, `SuscripcionResponse`).**
- **Errores:** `404` — `"Suscripción no encontrada"`; `400` — `"No se puede cancelar una suscripción en estado '{estado}'"`.

### PUT `/api/pagos/suscripcion/{id_suscripcion}/renovacion-automatica`

- **Auth:** `get_current_negocio`.
- **Path:** `id_suscripcion` (int).
- **Descripción:** Activa/desactiva la renovación automática.
- **Body:** `RenovacionAutomaticaRequest` `{ "renovacion_automatica": false }`.
- **Respuesta (200, `SuscripcionResponse`).**
- **Errores:** `404` — `"Suscripción no encontrada"`.

---

## 14. Estadísticas

Router: `app/routers/estadistica.py` → prefijo `/statistics`.

### GET `/api/statistics/business/{business_id}`

- **Auth:** `get_current_negocio` + verificación de propiedad (`negocio.id_negocio != business_id` → 403).
- **Path:** `business_id` (int).
- **Query:**
  | Parámetro | Tipo | Requerido | Default |
  |---|---|---|---|
  | `date_start` | string ISO (`YYYY-MM-DD`) | no | primer día del mes actual |
  | `date_end` | string ISO | no | hoy |
- **Descripción:** Devuelve el dashboard analítico del negocio vía `StatisticsService.get_dashboard_statistics`. Incluye:
  - `kpis`: `ingresoTotal`, `clientesActivos`, `servicioMasVendido`, `diaMasFacturado`, `horaMayorDemanda`, `ocupacionAgenda`.
  - `resumen`: `turnosHoy`, `turnosSemana`, `turnosMes`, `turnosPorDia` (7 días vs semana anterior).
  - `clientes`: `nuevos`, `recurrentes`, `inactivos`, `topVisitas`, `topCancelaciones`.
  - `servicios`: `items` (solicitados/ingresos/tiempo), `menosSolicitado`.
  - `ingresos`: `facturacionDiaria/Semanal/Mensual`, `ticketPromedio`, `evolucionMensual` (6 meses).
  - `agenda`: `horariosDemanda`, `horarioPico`, `diaMasTurnos`, `menorOcupacion`, `ocupacionPorcentaje`.
  - `asistencia`: `completados`, `cancelados`, `reprogramados`, `noShow`, `distribucion`, `tasaAsistencia`, `totalTurnos`.
  - `empleados`: por empleado (`nombre`, `turnos`, `ingresos`, `ocupacion`).
- **Respuesta (200, dict; los schemas de `estadistica.py` tipan el payload).**
- **Errores:** `403` — `"No tenés acceso a las estadísticas de este negocio"`; `422` — `business_id` no entero.

---

## Notas de verificación

- Endpoints **sin autenticación declarada** (identificados en esta referencia como "Auth: ninguna"): healthcheck, auth público, usuarios completos, negocios públicos/mapa/admin/backfill, empleados, clientes, categorías, horarios, georef, planes, `/turnos/por-rango` y el CRUD de turnos salvo `/estado`. No implica que sean públicos por diseño: es lo que el código verifica hoy.
- `admin_router.py` no expone endpoints funcionales (solo código comentado en su docstring).
- `/api/negocios/complete` es idéntico a `/api/negocios/` pero oculto del schema OpenAPI (`include_in_schema=False`).
- Los errores `422` provienen de la validación Pydantic de body/query (FastAPI), no de la lógica del servicio.