# AUTENTICACIÓN — Análisis del backend Turnogo

> Alcance: `app/routers/auth_router.py`, `app/services/auth_service.py`, `app/core/security.py`, `app/core/config.py`, `app/core/dependencies.py`, `app/models/usuario.py`.
> Estado por ítem: `IMPLEMENTADO` / `NO IMPLEMENTADO` / `NO DETERMINADO` (no verificable con el código actual).

---

## 1. Resumen ejecutivo

| Área | Estado | Nota |
|---|---|---|
| Registro con verificación de email | IMPLEMENTADO | Token de 24 h, confirma existencia previa (409) |
| Login usuario/contraseña | IMPLEMENTADO | bcrypt + JWT HS256, bloquea email sin verificar |
| 2FA por email (OTP) | IMPLEMENTADO (parcial) | No es obligatoria en `/auth/login`; OTP débil |
| Login con Google | IMPLEMENTADO | Con fugas de datos en `print()` |
| Verificación de email | IMPLEMENTADO | Token en URL (GET) |
| Reset de contraseña | IMPLEMENTADO | Token 24 h, no reutiliza contraseña vieja |
| Emisión/validación de JWT | IMPLEMENTADO | HS256, claims mínimos (`exp`, `sub`) |
| Refresh tokens / logout / revocación | NO IMPLEMENTADO | Un solo token; sin blacklist |
| Bloqueo de cuentas deshabilitadas | NO IMPLEMENTADO | `estado` nunca se chequea en auth |
| Límite de intentos (brute force) | NO IMPLEMENTADO | Ni login ni OTP |
| Secret key segura (obligatoria) | IMPLEMENTADO | Se eliminó el default; la app no arranca sin `SECRET_KEY` |

---

## 2. Registro de cuenta

- `IMPLEMENTADO` `unique` en email y username. `app/models/usuario.py:24-35`.
- `IMPLEMENTADO` Detección de usuario existente con error `409` **antes** de validar contraseña. `auth_service.py:50-65`. → revela si un email ya está registrado (enumeración de cuentas).
- `IMPLEMENTADO` Política de contraseña reforzada (regex): 12–16 caracteres, mayúscula, minúscula, número y carácter especial. `auth_service.py:40-46,67`.
- `IMPLEMENTADO` Hash bcrypt (passlib) **antes** de persistir. `auth_service.py:84` + `security.py:8,11`.
- `IMPLEMENTADO` Verificación de email obligatoria: el usuario nace con `email_verified=False` y un token `secrets.token_urlsafe(32)` (CSPRNG) con expiración de 24 h. `auth_service.py:77-91`.
- `IMPLEMENTADO` Envío de email de verificación vía Resend. `auth_service.py:97-100`.
- `NO IMPLEMENTADO` Límite de intentos/abuso en `/register` (flood de registros y envío de mails).
- `NO DETERMINADO` Si el valor `180` de `GOOGLE`… (n/a).

Evidencia de endpoints: `auth_router.py:34-48`.

---

## 3. Login con email y contraseña

- `IMPLEMENTADO` Se permite login por **email o username**. `auth_service.py:106-115`.
- `IMPLEMENTADO` Verificación de contraseña con `verify_password` (bcrypt, passlib). `auth_service.py:123-130`.
- `IMPLEMENTADO` Bloquea cuentas con email sin verificar (403). `auth_service.py:132-136` y `auth_service.py:365-369`.
- `IMPLEMENTADO` Respuesta de error genérica "Credenciales invalidas" (no revela si falló el usuario o la contraseña). `auth_service.py:117-130`.
- `IMPLEMENTADO` Emite JWT firmado (HS256) con `sub` = `id_us` y expiración `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60 min). `auth_service.py:138-147` + `security.py:19-22` + `config.py:6`.

### Hallazgo: la cuenta deshabilitada NO se bloquea
- `NO IMPLEMENTADO` El campo `estado` (`usuario.py:53-57`) **no se valida** en `login_user`, `verify_credentials` ni `get_current_user`. Un usuario con `estado=False` sigue autenticándose y recibiendo tokens.
- El único lugar donde se toca `estado` es `usuario_router.patch /{id}/estado` (`usuario_router.py:59-69`), que además es público (ver AUTORIZACION.md).

### Hallazgo: 2FA no es obligatoria en el login principal
- `POST /auth/login` (usa `login_user`) **no exige** 2FA y entrega un token de 60 min. El flujo OTP queda relegado a `/auth/verify-credentials`. Si el frontend usa `/login`, el factor doble se omite por completo. `auth_router.py:51-54`.

---

## 4. Verificación de credenciales + 2FA por email (OTP)

Flujo (todos públicos): `verify-credentials` → `verify-2fa` / `resend-code`.

- `IMPLEMENTADO` Re-chequeo de password y de email verificado. `auth_service.py:356-369`.
- `IMPLEMENTADO` **Token largo al recordar 2FA**: si `last_2fa_verified_at` es menor a `TWO_FACTOR_TOKEN_EXPIRE_HOURS` (default **9 horas**), reemite token sin pedir OTP. `auth_service.py:371-386`.
- `IMPLEMENTADO` OTP de 6 dígitos enviado por email (Resend). `auth_service.py:388-400`.
- `IMPLEMENTADO` `verify_2fa`: valida expiración y comparación del OTP, lo limpia y emite access token de 9 h. `auth_service.py:407-456`.
- `IMPLEMENTADO` `resend-code`: regenera OTP. `auth_service.py:459-517`.

### Deficiencias del OTP (riesgo alto)
- `NO IMPLEMENTADO` Límite de intentos de OTP → fuerza bruta posible sobre 6 dígitos (`verify_2fa` no cuenta fallos). `auth_service.py:426-439`.
- `NO IMPLEMENTADO` El OTP se guarda **en texto plano** en la BD (`usuario.otp_code`). `usuario.py:97-100`.
- `NO IMPLEMENTADO` OTP generado con `random.randint` (por defecto `random` Mersenne Twister, **no criptográfico**). `auth_service.py:388`.
- `NO IMPLEMENTADO` TTL de OTP de **9 horas** (`TWO_FACTOR_TOKEN_EXPIRE_HOURS`): ventana de ataque muy amplia. `config.py:7`, `auth_service.py:391-393`.
- `NO IMPLEMENTADO` El token de "recordado" dura 9 h con un solo factor previo (¿no re-pide OTP tras 9 h sin actividad?).
- `NO IMPLEMENTADO` No se invalidan todos los tokens/OTP al cambiar la contraseña, verificar email o el botón "logout".

---

## 5. Login con Google

- `IMPLEMENTADO` Validación del ID token con la librería `google-auth` (`verify_oauth2_token`, que chequea `aud`, issuer y expiración contra `GOOGLE_CLIENT_ID`). `auth_service.py:533-547`.
- `IMPLEMENTADO` Conflicto si el email ya existe con provider distinto a `google` (409). `auth_service.py:570-578`.
- `IMPLEMENTADO` Si es usuario nuevo: username derivado del email (con desambiguación numérica), `contrasena_us=None`, `auth_provider="google"`, requiere verificación de email. `auth_service.py:591-614`.

### Hallazgos de Google
- `NO IMPLEMENTADO` Se imprimen en consola `GOOGLE_CLIENT_ID`, los primeros 40 caracteres del token y el **payload completo del id_token** (fuga de datos personales del usuario en logs). `auth_service.py:528-531,540`.
- `NO IMPLEMENTADO` Google ya verificó el email, pero se crea el usuario con `email_verified=False` forzando una segunda verificación innecesaria. `auth_service.py:608`.
- `NO IMPLEMENTADO` `detail=str(e)` expone al cliente el mensaje interno del error de Google. `auth_service.py:545-547,553-554`.
- `NO DETERMINADO` Si el frontend usa código de autorización (con PKCE) u obtiene id_token en JS ("GIS"); el backend espera `id_token` en el body. `auth_router.py:56-70`.

---

## 6. Verificación de email

- `IMPLEMENTADO` Endpoint `GET /auth/verify-email/{token}`: valida token **y** expiración (24 h); marca `email_verified=True`, limpia token, emite access token de 60 min. `auth_service.py:287-333`.
- `NO IMPLEMENTADO` Token por URL (GET) → puede quedar en logs/registros del navegador y proxies.
- `NO IMPLEMENTADO` Respuesta distingue "Token inválido" vs "Token expirado" → permite inferir validez de un token. `auth_service.py:299-313` (menor).

---

## 7. Recuperación de contraseña

- `IMPLEMENTADO` `forgot-password`: respuesta genérica "Si el email existe, se enviará un enlace" → mitiga enumeración en *este* endpoint (aunque `/register` sí revela). `auth_service.py:181-186,210-214`.
- `IMPLEMENTADO` Token `secrets.token_urlsafe(32)` (CSPRNG) con expiración de 24 h. `auth_service.py:188-194`.
- `IMPLEMENTADO` El envío de email está en `try/except: pass`: si falla (o el email es inválido) **el error se traga silenciosamente**. `auth_service.py:202-208`.
- `IMPLEMENTADO` `reset-password`: valida token + expiración, aplica la misma regex de contraseña, rechaza que sea igual a la anterior y purga el token tras usarlo. `auth_service.py:217-284`.
- `IMPLEMENTADO` Confirma contraseña (`new_password != confirm_password`) en el router. `auth_router.py:108-112`.

### Deficiencia
- `NO IMPLEMENTADO` No se revocan los JWT vigentes cuando la contraseña cambia (una sesión activa robada sigue siendo válida hasta su expiración).

---

## 8. Emisión y validación de JWT

- `IMPLEMENTADO` Algoritmo HS256 con `SECRET_KEY`; claims: `exp` (fecha UTC) y `sub` (string del id). `security.py:19-22`.
- `NO IMPLEMENTADO` Sin claims `iat`, `aud`, `iss`, `nbf` ni `jti`. Sin `jti` no hay posibilidad de revocación selectiva.
- `IMPLEMENTADO` `get_current_user` decodifica y valida firma/expiración (python-jose rechaza `exp` vencida), convierte `sub` a entero y carga al usuario desde la BD. `dependencies.py:get_current_user`.
- `NO IMPLEMENTADO` `int(user_id)` sin validar → un `sub` no numérico (falsificado o mal emitido) lanza `ValueError` (HTTP 500) en vez de 401. `dependencies.py`.
- `IMPLEMENTADO` Esquema OpenAPI `OAuth2PasswordBearer(tokenUrl="/api/auth/login")`. `dependencies.py`.
- `NO IMPLEMENTADO` No existe "refresh token" real: hay un único token; el flujo "recordar 2FA" emite access token de 9 h como si fuera refresh.

### Deficiencias
- `NO IMPLEMENTADO` **Logout / revocación**: no hay endpoint de logout, blacklist ni denylist de `jti`. El token vive hasta su `exp`.
- `IMPLEMENTADO` `SECRET_KEY` es **obligatoria** (sin default): se eliminó el valor de ejemplo `"change-this-secret-in-production"` y `decouple` falla si no está definida. `config.py:4`. El arranque de la app depende de que el entorno la provea.
- `NO DETERMINADO` Almacenamiento del token en el cliente (localStorage/sessionStorage/cookies HttpOnly). Fuera del alcance del backend (frontend en `Turnexo_front`).

---

## 9. Resumen de riesgos (priorizados)

| # | Riesgo | Estado | Severidad |
|---|---|---|---|
| 1 | `SECRET_KEY` por defecto insegura | CORREGIDO (obligatoria) | — |
| 2 | 2FA no obligatoria en `/auth/login` (bypass por diseño) | NO implementado | ALTA |
| 3 | OTP: `random` no criptográfico, texto plano, TTL 9 h, sin límite de intentos | No implementado | ALTA |
| 4 | Sin rate limiting en login/OTP/register (brute force, flood de mails) | NO implementado | ALTA |
| 5 | Cuentas deshabilitadas (`estado=False`) siguen autenticándose | NO implementado | ALTA |
| 6 | Sin logout/revocación de JWT | NO implementado | MEDIA |
| 7 | Prints de `GOOGLE_CLIENT_ID` y payload de Google en consola | NO implementado | MEDIA |
| 8 | Política de contraseña limita a 16 caracteres (13 especial, etc.) | Implementado con límite | BAJA |
| 9 | Token de verificación por GET (queda en logs) | No implementado | BAJA |

---

## 10. Recomendaciones

1. Forzar `SECRET_KEY` (sin default) y dimensionarla ≥ 256 bits; rotación prevista.
2. Unificar el inicio de sesión: 2FA obligatoria en el único camino de login (eliminar `login_user` sin OTP o exigir OTP dentro de él).
3. OTP: generación con `secrets.randbelow`, expiry de 5–10 min, hasheado en BD (o token firmado efímero), contador de intentos con lockout y rate limiting.
4. Revisar/limitar el token de "recordar 2FA" (9 h) sin actividad.
5. Chequear `estado` del usuario en `get_current_user` y en `verify_credentials`.
6. Implementar `jti` + denylist o versionado de token (p. ej., `token_version` por usuario) para logout/revocación.
7. Eliminar `print()` con datos de Google y los `detail=str(e)`.
8. Reemplazar `python-jose` por `PyJWT` (mantenimiento activo).