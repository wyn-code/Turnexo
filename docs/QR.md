# QR — Backend TurnoGo

Documentación del sistema real de **códigos QR**, verificada contra `app/services/qr_service.py`, `app/services/email_service.py` y `app/core/config.py`. No existe routing, modelo ni base de datos dedicados al QR en el backend (verificado por búsqueda en el código).

---

## 1. Servicio (`app/services/qr_service.py`)

El módulo completo tiene **dos funciones** y ningún archivo adicional:

```python
def generar_qr_url(id_turno: int) -> str:
    """Build the scan URL encoded in the QR."""
    return f"{FRONTEND_URL}/dashboard/turnos?turno={id_turno}"


def generar_qr_png_bytes(id_turno: int) -> bytes:
    payload = generar_qr_url(id_turno)
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

Librería: `qrcode` (usa `qrcode.make(...)`). `FRONTEND_URL` proviene de `app/core/config.py` (`decouple.config("FRONTEND_URL", default="https://www.turnogo.app")`).

---

## 2. Payload y formato

- **Payload** (lo que codifica el QR): una **URL** → `{FRONTEND_URL}/dashboard/turnos?turno={id_turno}`.
- **Formato de imagen**: **PNG**, generado con `qrcode.make` (`box_size=8`, `border=2`) y devuelto como **bytes crudos** (`io.BytesIO`).
- **Único dato contenido**: el **ID del turno**, como parámetro de consulta `turno=<id>`. No hay más información en el payload (sin token, sin firma, sin datos del negocio/cliente/servicio).
- No se guarda el archivo en disco ni en base de datos: se genera en memoria, en cada invocación.

---

## 3. Relación con el turno

- El QR se genera **por `id_turno`**: `generar_qr_url(id_turno)` / `generar_qr_png_bytes(id_turno)`.
- **No** depende de ninguna otra entidad: el mismo turno siempre produce el mismo payload.
- La lectura/validación (escaneo) **no existe en el backend**: el payload apunta a una ruta del **frontend** (`/dashboard/turnos?turno=…`), que es quien visualiza el turno al escanear. No hay endpoint de verificación de QR en `app/routers/`.

---

## 4. Cómo se usa en el código

Único llamador del servicio (verificado por búsqueda):

- `email_service.send_booking_confirmation_email` → `qr_bytes = generar_qr_png_bytes(id_turno)` (línea 180) y lo adjunta al email de confirmación de turno (ver [EMAILS.md](./EMAILS.md)).

| Cosa | Dónde |
|---|---|
| Generación de URL | `qr_service.generar_qr_url` |
| Generación de PNG | `qr_service.generar_qr_png_bytes` |
| Uso | solo `email_service.send_booking_confirmation_email` |

---

## 5. Endpoints

**No existen endpoints de QR** en el backend:
- No hay `GET /api/qr/...` ni router de QR.
- No hay endpoint de **lectura/validación** (scanner). El escaneo lo resuelve la página del frontend a la que apunta el payload.

---

## 6. Almacenamiento

**No hay almacenamiento**: no existe columna en `Turno` ni tabla dedicada para el QR, ni cache/URL persistida. El PNG se regenera bajo demanda dentro del envío de email.

---

## 7. Validación y lectura

- **Validación en backend**: ninguna. No hay endpoint que verifique el QR ni su vigencia.
- **Lectura**: al escanear, el lector abre la URL `FRONTEND_URL/dashboard/turnos?turno=<id>`, es decir, la agenda/página del turno en el **frontend** (fuera de este repo).

---

## 8. Seguridad

- El payload contiene únicamente el `id_turno` en texto plano, sin firma ni secretos.
- No hay mecanismo anti-reutilización ni vencimiento del QR (no está ligado a `recordatorio_enviado` ni al estado del turno).
- La única señalización de "presentación" es el texto del email: el QR se presenta al momento del turno; la verificación de pertenencia/vigencia queda de la responsabilidad del consumidor del frontend (no implementada en el backend).

---

## 9. Observaciones reales

- `generar_qr_url` existe como función independiente pero solo se usa internamente por `generar_qr_png_bytes` (no hay endpoint que devuelva la URL).
- El QR **no** se regenera al cambiar los datos del turno: como su contenido es solo el id, un turno editado mantiene el mismo QR (el payload no cambia).
- El único lugar donde se entrega al cliente es el **email de confirmación** (adjunto, no inline exterior).