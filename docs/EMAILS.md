# Emails — Backend TurnoGo

Documentación del sistema real de **correos electrónicos**, verificada contra `app/services/email_service.py`, `app/core/config.py` (usando **solo los nombres** de variables, no valores) y los llamadores en `auth_service.py`, `usuario_service.py`, `turno_service.py` y `auth_router.py`.

---

## 1. Servicio utilizado

- **Proveedor**: **Resend** (SDK `resend`, API transaccional de emails).
- **Configuración**: `resend.api_key = RESEND_API_KEY` (variable de entorno definida en `app/core/config.py` vía `decouple.config("RESEND_API_KEY")`). **No se documentan valores**.
- **Remitente**: `FROM_ADDRESS = "TurnoGo <contacto@turnogo.app>"`.
- Formato de envío: `resend.Emails.send(params)` donde `params` usa `from`, `to`, `subject`, `html` y opcionalmente `attachments`.

---

## 2. Funciones del servicio (`app/services/email_service.py`)

| Función | Propagó | Contenido principal |
|---|---|---|
| `send_verification_email(email, token)` | verificación de cuenta | enlace `{FRONTEND_URL}/verify-email/{token}` + "expirará en 24 horas" |
| `send_reset_password_email(email, token)` | recuperación | enlace `{FRONTEND_URL}/restablecer-contrasena/{token}` + "expirará en 24 horas" |
| `send_cancellation_email(email, id_turno, nombre_negocio, nombre_servicio, fecha, hora, motivo)` | cancelación de turno | tabla con servicio/fecha/hora + bloque destacado con **motivo** |
| `send_booking_confirmation_email(email, id_turno, nombre_negocio, nombre_servicio, nombre_empleado, fecha, hora, direccion, telefono_negocio)` | confirmación de turno | datos de la reserva + **QR** adjunto |
| `send_two_factor_email(email, code)` | 2FA | OTP en plantilla estilizada ("10 minutos") |
| `send_otp_email(email, code)` | 2FA | OTP en plantilla simple ("10 minutos") |

---

## 3. Quién dispara cada email (y cuándo)

| Email | Llamador | Momento |
|---|---|---|
| `send_verification_email` | `auth_service.register_user` | al crear cuenta por contraseña |
| | `auth_service.login_with_google` | al crear cuenta por Google (primer login sin cuenta) |
| | `usuario_service.crear_usuario` | al crear usuario vía `POST /api/usuarios/` |
| | `auth_router` (`GET /auth/test-email`) | endpoint de prueba con dirección fija |
| `send_reset_password_email` | `auth_service.forgot_password` | al recuperar contraseña (solo si el email existe; el envío se envuelve en `try/except` que **traga** errores) |
| `send_otp_email` | `auth_service.verify_credentials` | primer paso del login 2FA (cuando la 2FA no está reciente) |
| | `auth_service.resend_otp_code` | reenvío del OTP |
| `send_booking_confirmation_email` | `turno_service.crear_turno` | **background** (`BackgroundTasks`) tras el commit del turno, **solo si el cliente tiene `email`** |
| `send_cancellation_email` | `turno_service.cambiar_estado_turno` | **background**, solo si: estado pasa a `CANCELADO`, el cliente tiene `email` **y** hay `rechazado_motivo` |
| `send_two_factor_email` | **ninguno** | definida pero **no invocada** por ningún servicio (función huérfana) |

> Hecho verificado: `send_two_factor_email` no aparece en ningún llamador del árbol `app/` y `tests/`.

---

## 4. Contenido de los emails

### Confirmación de turno (`send_booking_confirmation_email`)
- Asunto: `"Turno confirmado en {nombre_negocio}"`.
- HTML: encabezado "¡Tu turno en {nombre} está confirmado!", tabla con **servicio**, **profesional** (si existe `nombre_empleado`), **fecha** (`%d/%m/%Y`), **hora** (`%H:%M`), **dirección** y **teléfono del negocio** (los últimos dos solo si vienen); luego el **QR** y el texto "Código QR de tu turno #{id_turno}".
- Adjunto: `attachments` con `filename="qr_turno.png"`, `content= list(bytes del PNG)`, `content_type="image/png"`, `content_id="qr_turno"`; en el HTML se referencia como `<img src="cid:qr_turno">` (imagen embebida *inline*).

### Cancelación (`send_cancellation_email`)
- Asunto: `"Turno cancelado en {nombre_negocio}"`.
- HTML: título en rojo, tabla servicio/fecha/hora y un bloque `#fef2f2` con **motivo** de cancelación, cierre "Reservado a través de TurnoGo".

### Verificación y reset
- Enlaces a `{FRONTEND_URL}/verify-email/{token}` y `{FRONTEND_URL}/restablecer-contrasena/{token}`, vigencia declarada de 24 h.

### OTP (2FA)
- `send_otp_email`/`send_two_factor_email`: código de 6 dígitos displayed en grande; el texto dice "validez de **10 minutos**".

---

## 5. QR en los emails

El **único** email que incluye QR es `send_booking_confirmation_email`. Relación completa con QR:

```
crear_turno (turno_service)
  → BackgroundTasks → send_booking_confirmation_email(cliente.email, id_turno, …)
      → generar_qr_png_bytes(id_turno)          (qr_service)
      → locale {FRONTEND_URL}/dashboard/turnos?turno={id_turno}
      → attach QR (PNG bytes) con content_id "qr_turno" → <img src="cid:qr_turno">
```

Ver [QR.md](./QR.md) para el payload/formato. El email de **cancelación no** lleva QR.

---

## 6. Relación con la confirmación de turnos

- La **confirmación del turno es el estado CONFIRMADO** (ver [ESTADOS_TURNO.md](./ESTADOS_TURNO.md)): al crearse un turno, el backend ya lo fija como CONFIRMADO.
- El email de confirmación se envía **después del `db.commit()`** y **en background**, por lo que no bloquea la respuesta HTTP 201. Si falla, el turno ya existe (el email es best-effort).
- Los datos que viajan en el email (negocio, servicio, empleado, dirección) se leen de la sesión en el momento del envío; si no hay relación cargada, se usan fallbacks (`"TurnoGo"`, `"Servicio"`).
- La cancelación se notifica **solo cuando el cambio de estado llega desde un estado distinto de CANCELADO** y hay motivo (condición `es_cancelacion and cliente_email and datos.rechazado_motivo`).

---

## 7. Manejo de errores (real)

| Llamador | Comportamiento ante fallo |
|---|---|
| `send_verification_email` | `resend.Emails.send` directo; **excepciones propagan** al service que la llama |
| `send_reset_password_email` | internamente `try/except` con `print` y `raise` (repropaga); además `forgot_password` envuelve la llamada en `try/except Exception: pass` → **errores de envío en reset se silencian** (el usuario igual ve "Si el email existe…") |
| `send_otp_email` | llamada directa; excepciones propagan a `verify_credentials`/`resend_otp_code` |
| `send_two_factor_email` | `try/except` con `print` y `raise` (no usada) |
| `send_booking_confirmation_email` | si `email` vacío → `return` temprano; fallo de Resend **no** afecta al turno (background) |
| `send_cancellation_email` | idem: `return` temprano sin email; fallo en el envío no revierte el cambio de estado |

- **Ningún email** se reenvía automáticamente; no hay cola de reintentos ni estado de "enviado/no enviado" por email. El flag `recordatorio_enviado` del turno pertenece al scheduler de recordatorios (ver [RESERVAS.md](./RESERVAS.md)), no a estos emails.

---

## 8. Observaciones reales

- Hay dos plantillas de OTP (`send_two_factor_email` sin llamadores y `send_otp_email` con llamadores): la usada es `send_otp_email`.
- El texto del email dice "el código vence en 10 minutos", pero la expiración **efectiva** del OTP en `auth_service` es `TWO_FACTOR_TOKEN_EXPIRE_HOURS` (default configurado en horas, ver `app/core/config.py`) — es una divergencia real entre el copy y el código.
- `FRONTEND_URL`, `BACKEND_URL` y `RESEND_API_KEY` se referencian solo por nombre en esta doc; no se muestran valores.