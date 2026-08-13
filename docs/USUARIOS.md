# Usuarios y autenticación — Backend TurnoGo

Documentación del módulo de **usuarios y auth**, verificada contra `app/models/usuario.py`, `app/services/usuario_service.py`, `app/services/auth_service.py`, `app/routers/usuario_router.py`, `app/routers/auth_router.py`, `app/schemas/usuario_schema.py`, `app/schemas/auth_schema.py`, `app/core/security.py`, `app/core/config.py` y `app/core/roles.py`.

---

## 1. Modelo `Usuario` (tabla `usuarios`)

`app/models/usuario.py` — clase `Usuario`, PK `id_us`.

| Columna | Tipo | Null | Default | Notas |
|---|---|---|---|---|
| `id_us` | Integer | no | — | **PK** index |
| `usuario_us` | String(50) | no | — | **UNIQUE** |
| `email_us` | String(100) | no | — | **UNIQUE** + index |
| `contrasena_us` | String(255) | sí | — | hash bcrypt; `None` solo para cuentas Google |
| `role` | String(20) | no | `"duenio"` | valores en `core/roles.py`: `Roles.ADMIN = "admin"`, `Roles.DUENIO = "duenio"` |
| `created_at` | DateTime | no | `datetime.now` | |
| `estado` | Boolean | no | `True` | activo/inactivo (soft); ver nota en §8 |
| `email_verified` | Boolean | no | `False` | gate de login |
| `verification_token` | String(255) | sí | — | token de 24 h |
| `verification_token_expiration` | DateTime | sí | — | |
| `reset_token` | String(255) | sí | — | |
| `reset_token_expiration` | DateTime | sí | — | |
| `otp_code` | String(10) | sí | — | OTP 2FA de 6 dígitos |
| `otp_expires_at` | DateTime | sí | — | |
| `last_2fa_verified_at` | DateTime | sí | — | fecha de la última 2FA |
| `auth_provider` | String(20) | no | `"local"` | `local` \| `google` |

**Relaciones:** `negocios` 1—N → `Negocio.usuario_id` (`back_populates="usuario"`, `cascade="all, delete-orphan"`). En la práctica es **1:1** porque `negocio.usuario_id` es **UNIQUE**.

---

## 2. Schemas

### `app/schemas/usuario_schema.py`
| Clase | Campos | Notas |
|---|---|---|
| `UsuarioBase` | `usuario_us: str`, `email_us: EmailStr` | |
| `UsuarioCreate` | + `contrasena_us: str` | **sin** validación de longitud (la validación fuerte está en `RegisterRequest`) |
| `UsuarioUpdate` | `usuario_us`, `email_us`, `contrasena_us` (Optional) | |
| `UsuarioResponse` | + `id_us`, `created_at`, `role`, `estado` | `from_attributes=True` |
| `UsuarioAdminResponse` | `id_us`, `usuario_us`, `email_us`, `role_us`, `habilitado`, `negocio`, `estado` | |
| `EstadoUsuarioRequest` | `estado: bool` | |

### `app/schemas/auth_schema.py`
| Clase | Validaciones |
|---|---|
| `RegisterRequest` | `usuario_us` 3–30; `email_us: EmailStr`; `contrasena_us` 12–16 |
| `LoginRequest` | `email_us: str` (acepta email **o** usuario); `contrasena_us` 12–16 |
| `VerifyCredentialsResponse` | `requires_2fa: bool = True`, `message: str` |
| `Verify2FARequest` | `email_us: EmailStr`, `otp_code` de **exactamente 6** caracteres |
| `ResendCodeRequest` | `email_us: EmailStr` |
| `TokenResponse` | `access_token: str`, `token_type = "bearer"` |
| `AuthResponse` | `usuario: UsuarioResponse`, `token: TokenResponse` |
| `GoogleLoginRequest` | `id_token: str` |
| `ForgotPasswordRequest` | `email_us: EmailStr` |
| `ResetPasswordRequest` | `new_password` y `confirm_password` 12–16 |

---

## 3. Endpoints

### `app/routers/auth_router.py` (`prefix="/auth"`, montado en `/api`)

| Endpoint | Función de servicio | Auth |
|---|---|---|
| `POST /api/auth/register` | `register_user` | no |
| `POST /api/auth/login` | `login_user` | no |
| `POST /api/auth/google` | `login_with_google` | no |
| `GET /api/auth/me` | `build_me_response` | **sí** (`get_current_user`) |
| `GET /api/auth/test-email` | `send_verification_email` (fijo) | no |
| `POST /api/auth/forgot-password` | `forgot_password` | no |
| `POST /api/auth/reset-password/{token}` | `reset_password` | no |
| `GET /api/auth/verify-email/{token}` | `verify_email` | no |
| `POST /api/auth/verify-credentials` | `verify_credentials` | no |
| `POST /api/auth/verify-2fa` | `verify_2fa` | no |
| `POST /api/auth/resend-code` | `resend_otp_code` | no |

### `app/routers/usuario_router.py` (`prefix="/usuarios"`, montado en `/api`)

| Endpoint | Función de servicio | Auth |
|---|---|---|
| `GET /api/usuarios/` | `ver_usuarios` | **no** (solo `get_db`) |
| `GET /api/usuarios/admin` | `ver_usuarios_admin` | **no** |
| `GET /api/usuarios/{usuario_id}` | `ver_usuario_por_id` | **no** |
| `POST /api/usuarios/` | `crear_usuario` | **no** |
| `PUT /api/usuarios/{usuario_id}` | `actualizar_usuario` | **no** |
| `PATCH /api/usuarios/{usuario_id}/estado` | `cambiar_estado_usuario` | **no** |
| `DELETE /api/usuarios/{usuario_id}` | `borrar_usuario` | **no** |

> **Hecho relevante**: los endpoints `/usuarios/*` **no** exigen token (dependen solo de `get_db`), a diferencia de `/auth/me`. La única verificación de identidad está en `get_current_user` (`app/core/dependencies.py`), usado por `/auth/me`, creación de servicios, negocio `/me`, plan/pago/estadística y el cambio de estado de turno.

---

## 4. Servicios

### `app/services/usuario_service.py`
| Función | Lógica |
|---|---|
| `ver_usuarios` | todos los usuarios |
| `ver_usuario_por_id` | por `id_us` |
| `crear_usuario` | 409 si `usuario_us` o `email_us` ya existen; hash bcrypt; `email_verified=False`; token de verificación con expiración `utcnow()+24h`; `commit`; envía email de verificación |
| `actualizar_usuario` | 409 si el cambio choca con otro usuario (excluye el propio `id_us`); `strip()`; re-hash si cambia contraseña |
| `borrar_usuario` | borrado **físico** |
| `ver_usuarios_admin` | usuarios + negocio del usuario (`joinedload(Usuario.negocios)`), formatea campo `negocio` con nombres separados por coma |
| `cambiar_estado_usuario` | 404 si no existe; setea `estado` |

### `app/services/auth_service.py`
| Función | Lógica |
|---|---|
| `register_user` | 409 si email **o** usuario ya existen (`or_`); valida `PASSWORD_REGEX`; hash bcrypt; `email_verified=False`; token + email de verificación |
| `login_user` | busca por `email_us == data.email_us` **o** `usuario_us == data.email_us`; 401 si no existe; `verify_password`; **403 si `email_verified` es False**; emite `create_access_token` |
| `build_me_response` | busa `Negocio.usuario_id == id_us`; devuelve `has_business`, `negocio_id`, `negocio_slug`, `role`, datos del usuario |
| `forgot_password` | respuesta idéntica exista o no el email (evita enumeración); genera `reset_token` + 24 h; envía email |
| `reset_password` | 400 token inválido/expirado; valida regex; **rechaza igual a la anterior**; limpia token |
| `verify_email` | 400 token inválido/expirado; marca `email_verified=True` y limpia token; **devuelve un `access_token` en el cuerpo** |
| `verify_credentials` | primer paso del login 2FA: valida credenciales + `email_verified`; si `last_2fa_verified_at >= ahora - TWO_FACTOR_TOKEN_EXPIRE_HOURS` devuelve token directo; si no, genera OTP de 6 dígitos, lo persiste con expiración `TWO_FACTOR_TOKEN_EXPIRE_HOURS` y lo envía por email |
| `verify_2fa` | 401 usuario no existe / OTP expirada / código incorrecto; limpia `otp_code` y `otp_expires_at`, setea `last_2fa_verified_at`, devuelve `TokenResponse` |
| `resend_otp_code` | regenera y reenvía OTP; también respeta la ventana de `last_2fa_verified_at` |
| `login_with_google` | verifica `id_token` con `verify_oauth2_token` (Google); 409 si el email ya existe con `auth_provider != "google"`; si existe local, emite token; si no, crea usuario con `contrasena_us=None`, `auth_provider="google"`, `email_verified=False`, `username` derivado del email con sufijo numérico si choca, y envía email de verificación. Devuelve `TokenResponse` o `None` (cuando recién crea → el router responde "revisá tu email") |

---

## 5. Seguridad y configuración

- **Hash**: bcrypt vía `passlib` (`app/core/security.py`, `pwd_context = CryptContext("bcrypt")`). `get_password_hash`/`verify_password` hacen `.strip()` de la contraseña.
- **JWT**: HS256, payload `{"exp", "sub"}`; `SECRET_KEY` desde env (default `"change-this-secret-in-production"`).
- **Expiración**: `ACCESS_TOKEN_EXPIRE_MINUTES` (default **60** min); `TWO_FACTOR_TOKEN_EXPIRE_HOURS` (default **9** h).
- **Regla de contraseña** (`PASSWORD_REGEX`): 12–16 caracteres con al menos una minúscula, una mayúscula, un dígito y un carácter especial de `@$!%*?&.#_-`.
- **Emails** (Resend, `email_service.py`): verificación → `FRONTEND_URL/verify-email/{token}`; reset → `FRONTEND_URL/restablecer-contrasena/{token}`; ambos con vigencia de 24 h.

---

## 6. Relaciones

- `Usuario 1—N Negocio` (1:1 real por `usuario_id` UNIQUE) — el usuario `posee` un negocio del que agrega servicios/empleados/horarios.
- `get_current_user` (dependencia) resuelve el `Usuario` desde el `sub` del JWT; `get_current_negocio` resuelve su `Negocio` (`Negocio.usuario_id == id_us`, 404 si no tiene).
- **Rol**: `role` default `"duenio"`. El único uso real de `"admin"` en el código: `negocio_service.actualizar_negocio` (bypass de propiedad) y `eliminar_negocio` (obligatorio). `admin_router.py` exige admin pero **no está montado** en `main.py`.

---

## 7. Flujo de datos (registro → login → 2FA)

```
POST /auth/register          → valida regex → hashea → crea (email_verified=False) → email con token 24h
GET /auth/verify-email/{t}   → marca email_verified=True → emite access_token (en el cuerpo)
POST /auth/verify-credentials→ valida credenciales + email_verified
                              ├─ 2FA reciente (<=9h) → access_token
                              └─ genera OTP 6 dígitos (EMAIL) y lo persiste
POST /auth/verify-2fa        → valida OTP + expiración → access_token
POST /auth/login             → (flujo sin 2FA) → access_token (60 min)
GET /auth/me                 → token Bearer → get_current_user → negocio/slug/role
```

---

## 8. Observaciones reales (sin inventar)

- `estado` (booleano) **no** se consulta ni en `login_user` ni en `get_current_user`: un usuario inactivo puede seguir logueando vía el flujo sin 2FA. Solo lo tocan `cambiar_estado_usuario`, `ver_usuarios_admin` y el endpoint `/usuarios/{id}/estado`.
- Existen **dos** creaciones de usuario equivalentes: `usuario_service.crear_usuario` (sin validar complejidad de contraseña) y `auth_service.register_user` (con `PASSWORD_REGEX`). Ambas envían el email de verificación.
- Los usuarios creados por Google quedan `email_verified=False` hasta verificar el email.

---

## 9. Cómo se relaciona con los turnos

- El turno pertenece a un **negocio**, y el negocio pertenece a un **usuario**. El backend valida titularidad al cambiar el estado de un turno: `PUT /api/turnos/{id}/estado` usa `get_current_negocio` y `cambiar_estado_turno` devuelve **403** si `turno_db.id_negocio != id_negocio` (`"Este turno no pertenece a tu negocio"`).
- `get_current_user` protege además: creación/edición de servicios (`servicio_router`) por propiedad del negocio (`negocio.usuario_id == current_user.id_us`).
- El campo `has_business`/`negocio_id` de `GET /auth/me` habilita al frontend a saber si el usuario ya completó su negocio antes de operar con turnos.