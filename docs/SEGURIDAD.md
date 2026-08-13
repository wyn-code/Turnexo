# SEGURIDAD — Análisis transversal del backend Turnogo

> Alcance: infraestructura de la app FastAPI (`app/main.py`, `app/core/*`, `app/db/*`), migraciones Supabase (`supabase/migrations/*`), manejo de terceros (Google, Resend, Mercado Pago, Mapbox) y dependencias (`requirements.txt`).
> Estado por ítem: `IMPLEMENTADO` / `NO IMPLEMENTADO` / `NO DETERMINADO`.

---

## 1. Resumen ejecutivo

| Área | Estado | Severidad |
|---|---|---|
| Secretos vía entorno + `.gitignore` | IMPLEMENTADO (con default riesgoso) | MEDIA |
| `SECRET_KEY` sin default | IMPLEMENTADO (ahora obligatoria) | — |
| CORS | IMPLEMENTADO (lista fija) | BAJA |
| Rate limiting | NO IMPLEMENTADO | ALTA |
| Headers de seguridad / HTTPS redirect | NO IMPLEMENTADO | MEDIA |
| Inyección SQL | Mitigado (ORM) | BAJA |
| RLS en Supabase | IMPLEMENTADO (políticas agregadas) | BAJA residual |
| Validación de inputs | IMPLEMENTADO (Pydantic + regex) | BAJA |
| Integridad de webhook Mercado Pago | NO IMPLEMENTADO | ALTA |
| Logging / auditoría | NO IMPLEMENTADO (prints de secretos) | MEDIA |
| Endpoints de prueba/mantenimiento activos | NO IMPLEMENTADO | MEDIA |
| Dependencias auditadas | NO DETERMINADO | — |

---

## 2. Gestión de secretos y configuración

- `IMPLEMENTADO` Config vía `decouple` (`python-decouple`): lee variables de entorno y `.env`. `config.py:1-4`.
- `IMPLEMENTADO` `.env` y `.env.*` en `.gitignore` (no se comitean las claves).
- `IMPLEMENTADO` `SECRET_KEY` ahora es **obligatoria**: se eliminó el default `"change-this-secret-in-production"`. Si el entorno no la define, la app no arranca. `config.py:4`.
- `IMPLEMENTADO` Resto de secretos **sin default** (`RESEND_API_KEY`, `MAPBOX_ACCESS_TOKEN`, `BACKEND_URL`, `MERCADOPAGO_ACCESS_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) → el proceso arranca y falla si no están definidos. `config.py:8-14`.
- `NO DETERMINADO` Uso de `GOOGLE_CLIENT_SECRET`: está en config pero el flujo de Google del backend solo usa `GOOGLE_CLIENT_ID` (`auth_service.py:19-22,533-538`). Verificar si corresponde un flujo OAuth con secret.
- `NO IMPLEMENTADO` No hay rotación de secretos, ni manager tipo Vault/SSM: dependiente del entorno de despliegue.

---

## 3. CORS

- `IMPLEMENTADO` `CORSMiddleware` con orígenes fijos: `http://localhost:5173`, `https://www.turnogo.app`, `https://turnogo.app`; `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`. `main.py:22-34`.
- `NO IMPLEMENTADO` Lista **hardcodeada** (no configurable por entorno) → si el frontend se sirve desde otro dominio (staging, dominio nuevo) habrá que tocar código.
- `BAJA` Dado que la API usa Bearer token en header (no cookies), el riesgo CSRF con `allow_credentials` es bajo; con cookies es alto.

---

## 4. Rate limiting / brute force

- `NO IMPLEMENTADO` No hay middleware ni dependencia de rate limiting (sin `slowapi`/`limits` en `requirements.txt`; sin middleware en `main.py`).
- Impacto directo:
  - Fuerza bruta en `POST /auth/login` y `POST /auth/verify-credentials` (`auth_router.py:51,130`).
  - Fuerza bruta del OTP (6 dígitos) en `POST /auth/verify-2fa` (`auth_service.py:426-439`).
  - Abuso en `POST /auth/register` y `POST /auth/forgot-password` (flood de emails vía Resend).
  - Scraping masivo de datos de los endpoints públicos (AUTORIZACION.md §4).

---

## 5. Cabeceras de seguridad y transporte

- `NO IMPLEMENTADO` Sin middleware de cabeceras (`X-Content-Type-Options`, `CSP`, `Referrer-Policy`, etc.).
- `NO IMPLEMENTADO` Sin redirect HTTP→HTTPS en el backend (el TLS live en el borde — Vercel — NO DETERMINADO qué hace el proxy del host del backend).
- `NO IMPLEMENTADO` Sin logging estructurado intermedio (`logs` autocontained en app), salvo `logger` en `pago_router.py:18`.
- `IMPLEMENTADO` Healthchecks expuestos por defecto: `GET /` (mensaje + 🚀) y `GET /db-test` (conecta a la BD y responde "conexion OK con postgres"). `main.py:36-46`.

---

## 6. SQL / acceso a datos

- `IMPLEMENTADO` Acceso vía SQLAlchemy ORM (parámetros parametrizados → sin inyección SQL clásica). Única SQL cruda: `text("SELECT 'conexion OK con postgres'")` en el healthcheck. `main.py:40-46`.
- `IMPLEMENTADO` `get_current_user` consulta con filtro por PK (`Usuario.id_us == id`). `dependencies.py`.
- `NO IMPLEMENTADO` `int(user_id)` sin `try/except` → `sub` inválido genera `ValueError` (500) en vez de 401 (menor, ver AUTENTICACION §8).
- `NO IMPLEMENTADO` Timing: no hay comparación de tiempo constante específica; bcrypt mitiga razonablemente en `verify_password`.

---

## 7. Row Level Security (Supabase)

- `IMPLEMENTADO` RLS ya estaba **habilitado** en todas las tablas del esquema `public`, pero **sin ninguna política** (verificado con `list_tables` y los advisors de seguridad).
- `IMPLEMENTADO` Se crearon políticas de lectura pública (`public_read_*`) para el catálogo público: `negocio`, `servicio`, `estado_turno`, `categorias`, `localidades`, `provincia`, `negocio_imagen`, `horarios_negocio`, `planes`. Migración: `supabase/migrations/20260812120000_rls_politicas.sql`.
- `IMPLEMENTADO` Las tablas sensibles (`usuarios`, `turno`, `cliente`, `empleado`, `suscripciones`, `plan_features`) quedan **sin políticas** → `anon`/`authenticated` no pueden leerlas vía PostgREST.
- `NO DETERMINADO` La aplicación conecta por `DATABASE_URL` con un rol que **bypasses RLS** (postgres/service_role), por lo que las políticas no alteran su comportamiento; verificadas con datos accesibles y tests (122 OK). **Recomendación:** para que RLS proteja también la capa de la app, conectar con un rol no-bypass y definir políticas por `auth.uid()` (requiere vincular `usuarios.id_us` con Supabase Auth).

---

## 8. Validación de entrada

- `IMPLEMENTADO` Schemas Pydantic en cada router (login, register, 2FA, reset, negocio, turno, pago…).
- `IMPLEMENTADO` Regex de contraseña 12–16 con mayúscula/minúscula/número/especial y rechazo de contraseña reutilizada. `auth_service.py:40-46,246-271`.
- `IMPLEMENTADO` Separación de schemas `UsuarioCreate` / `UsuarioUpdate` / `UsuarioAdminResponse` (define qué campos expone una respuesta admin). `usuario_router.py:6`.
- `NO DETERMINADO` Rango/longitud de `otp_code` y `verification_token` sí limitados por columna `String` (10 y 255) en DB (`usuario.py:69,97`), pero la validación en schema del OTP no fue verificada.

---

## 9. Almacenamiento de datos sensibles

- `IMPLEMENTADO` Contraseñas: hash bcrypt (passlib). `security.py:8-16`.
- `NO IMPLEMENTADO` **OTP en texto plano** en `usuario.otp_code` (sensible a lectura directa de BD). `usuario.py:97-100`, `auth_service.py:390-394`.
- `NO IMPLEMENTADO` JWT: sin `jti`/versión de token → imposible revocar un token comprometido (ver AUTENTICACION §8).
- `NO DETERMINADO` Almacenamiento del JWT en el cliente (localStorage/sessionStorage) — del frontend.

---

## 10. Integridad y terceros

### Mercado Pago
- `IMPLEMENTADO` SDK oficial (`mercadopago==3.3.0`); el webhook consulta a MP (`payment().get(payment_id)`) en lugar de confiar en el body. `pago_router.py:47-61`.
- `NO IMPLEMENTADO` **El webhook no valida la firma** (`X-Signature` / `x-signature` de MP) ni otra autorización → cualquier llamada al endpoint con un `payment_id` conocible de una venta aprobada de otra cuenta puede disparar `procesar_pago_exitoso`. `pago_router.py:39-65`.
- `NO IMPLEMENTADO` No hay resguardo de idempotencia/replay fuera del manejo por DB del servicio.
- `NO DETERMINADO` Qué valida `payment_service.procesar_pago_exitoso` (negocio/plan + estado).

### Google (login)
- `NO IMPLEMENTADO` `print()` de `GOOGLE_CLIENT_ID`, prefijo del token y **payload completo del id_token** en stderr. Fuga de datos en logs. `auth_service.py:528-531,540`.
- `IMPLEMENTADO` Verificación estricta de `id_token` vía `google-auth` (aud + exp + issuer). `auth_service.py:533-547`.

### Email (Resend)
- `IMPLEMENTADO` Uso de la SDK oficial (`resend>=2.30.1`); tokens de verificación y reset con `secrets.token_urlsafe(32)` (CSPRNG) y expiración 24 h. `auth_service.py:77,188-194`.
- `NO IMPLEMENTADO` `except Exception: pass` silencia errores de envío. `auth_service.py:202-208`.

### Mapbox
- `IMPLEMENTADO` Token vía entorno. `config.py:10`.

---

## 11. Endpoints de prueba y mantenimiento expuestos

- `NO IMPLEMENTADO` `GET /auth/test-email` envía un email real a una cuenta hardcodeada, sin auth. `auth_router.py:79-89`. **Eliminar.**
- `NO IMPLEMENTADO` `POST /negocios/admin/rebuild-data` y `POST /negocios/backfill-coordenadas` ejecutan backfills sin token. `negocio_router.py:19-21,117-121`. **Proteger o eliminar.**
- `IMPLEMENTADO` `GET /db-test` expone conectividad a la BD (de activo por defecto).
- `NO DETERMINADO` Exposición de `/docs` (Swagger) en producción: por defecto FastAPI lo habilita.

---

## 12. Dependencias y auditoría

- `NO DETERMINADO` No hay evidencia de escaneo de vulnerabilidades (dependabot, `pip-audit`) en el repo.
- `MEDIA` `python-jose` (JWT) tiene mantenimiento esporádico; `passlib 1.7.4` no maneja bien `bcrypt>=4.x` (warnings en runtime); sugeridas: **PyJWT** para JWT y `pwdlib[argon2]`/directo `bcrypt` para hash.
- `MEDIA` `pylint` presente como única herramienta de calidad en `requirements.txt`.

---

## 13. Riesgos priorizados

| # | Riesgo | Estado | Severidad |
|---|---|---|---|
| 1 | RLS sin políticas en tablas sensibles | CORREGIDO (políticas de catálogo público creadas; sensibles denegadas) | BAJA residual |
| 2 | Webhook MP sin verificación de firma | NO implementado | ALTA |
| 3 | Sin rate limiting (login/OTP/register) | NO implementado | ALTA |
| 4 | `SECRET_KEY` default inseguro | CORREGIDO (ahora obligatoria) | — |
| 5 | OTP en texto plano + `random` no criptográfico | NO implementado | ALTA |
| 6 | Prints de datos de Google en logs | NO implementado | MEDIA |
| 7 | Endpoints de prueba/mantenimiento activos sin auth | NO implementado | MEDIA |
| 8 | `/db-test` público / healthchecks verbosos | No implementado | BAJA |
| 9 | CORS fijo y permisivo (`*` métodos/headers) | Implementado | BAJA |

---

## 14. Recomendaciones (orden de prioridad)

1. **HECHO** — RLS: políticas de catálogo público creadas (migración `20260812120000_rls_politicas.sql`). Pendiente avanzado: vincular `usuarios.id_us` con Supabase Auth y conectar la app con rol `authenticated` para que RLS proteja también a la capa Python.
2. Proteger el **webhook de MP** verificando la firma (`X-Signature`) o revalidando el `preference_id`/`external_reference` contra el negocio.
3. Añadir **rate limiting** (p. ej. `slowapi`) al menos en `/auth/login`, `/auth/verify-credentials`, `/auth/verify-2fa`, `/auth/resend-code`, `/auth/register`.
4. **HECHO** — `SECRET_KEY` ahora es obligatoria (sin default); mantener ≥ 256 bits y rotación en producción.
5. Reemplazar `random` por `secrets` en el OTP; hashear el OTP y reducir su TTL.
6. Eliminar todos los `print()` con datos de sesión/claves; implantar logging estructurado y desactivar `/docs` y `/db-test` en producción.
7. Aplicar las cabeceras de seguridad (CSP, `X-Content-Type-Options`, `Referrer-Policy`) vía middleware del host.
8. Eliminar/proteger los endpoints de mantenimiento (`rebuild-data`, `backfill-coordenadas`, `test-email`).
9. Migrar a PyJWT + límite de `bcrypt` en `passlib` o `pwdlib`; agregar `pip-audit`/Dependabot al CI.