# Pagos (MercadoPago) — Backend TurnoGo

Documentación del flujo de pagos, verificada contra `app/services/payment_service.py` y `app/routers/pago_router.py`.

---

## 1. Componentes

| Pieza | Ubicación |
|---|---|
| SDK de MercadoPago | `import mercadopago` → `sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)` (módulo de `app/services/payment_service.py`) |
| Credencial | `MERCADOPAGO_ACCESS_TOKEN` desde `app/core/config.py` (`decouple.config("MERCADOPAGO_ACCESS_TOKEN")`) — **no exponer valor alguno, es secreto** |
| URLs de entorno | `BACKEND_URL`, `FRONTEND_URL` desde `app/core/config.py` |
| Router | `app/routers/pago_router.py` — `prefix="/pagos"`, montado en `/api` |
| Modelos | `Suscripcion`, `Plan`, `Negocio` (ver [SUSCRIPCIONES.md](./SUSCRIPCIONES.md)) |

**Tarjeta de pago usada**: *Checkout Pro* vía **preferencias**: el backend crea una `preference` y devuelve `init_point` (o `sandbox_init_point`) para que el navegador la abra. No hay suscripciones recurrentes de MercadoPago ni procesamiento de tarjeta local.

---

## 2. Flujo completo

```
TurnoGo (frontend)
   │  1. POST /api/pagos/crear-preferencia  { id_plan }
   ▼
Backend
   │  2. valida plan activo
   │  3. cancela pendientes previas del negocio
   │  4. SDK  preference().create(...)   ──►  MercadoPago
   │  5. persiste Suscripcion "pendiente" (con preference_id)
   │  6. responde { init_point, preference_id }
   ▼
TurnoGo (frontend)
   │  7. redirige al navegador a init_point  (Checkout Pro)
   ▼
MercadoPago
   │  8. el cliente paga
   │  9. redirige a back_url (success/failure/pending)  ──►  TurnoGo frontend
   │ 10. envía webhook payment  ──────────────────────────►  Backend /api/pagos/webhook
   ▼
Backend
   │ 11. valida pago (payment.status == "approved")
   │ 12. parsea external_reference "id_negocio:id_plan"
   │ 13. procesar_pago_exitoso → activa/cancela suscripciones
   ▼
   Respuesta final a TurnoGo (backend → MP 200 "ok"; frontend ya recibió el pago vía back_url)
```

---

## 3. Creación de preferencia (`crear_preferencia_mp`)

Endpoint: **`POST /api/pagos/crear-preferencia`** (protegido con `get_current_negocio`).

1. **Validación** (router): el `Plan` debe existir y estar `activo` → 404 `"Plan no encontrado o inactivo"`.
2. **`external_reference`**: `f"{negocio.id_negocio}:{plan.id_plan}"` → es la llave que conecta el webhook con el negocio/plan.
3. **Cancela pendientes previas** del negocio (`estado == "pendiente"` → `"cancelada"`) y hace `commit`.
4. **Datos de la preferencia** que se envían a MercadoPago:
   - `items`: `title = plan.nombre`, `quantity = 1`, `unit_price = float(plan.precio)`, `currency_id = "ARS"`.
   - `back_urls`: `success`, `failure`, `pending` → `FRONTEND_URL/pagos/resultado`.
   - `auto_return = "approved"`.
   - `notification_url` → `BACKEND_URL/api/pagos/webhook`.
   - `external_reference` (id_negocio:id_plan).
   - `date_of_expiration` → ahora + **24 h** (ISO, UTC).
5. **SDK**: `sdk.preference().create(preference_data)`.
   - Excepción → log + **502** `"Error al comunicarse con MercadoPago: {exc}"`.
   - `response.status` no en `(200, 201)` → **502**.
   - `response` sin `id` → **502** `"MercadoPago no devolvió una preferencia válida"`.
6. **Selección del checkout**:
   ```python
   _es_test = str(MERCADOPAGO_ACCESS_TOKEN).startswith("TEST-")
   init_point = (response["sandbox_init_point"]
                 if _es_test and response.get("sandbox_init_point")
                 else response["init_point"])
   ```
   → Si el token es de pruebas (`TEST-…`) y MercadoPago devolvió `sandbox_init_point`, se usa ese; si no, `init_point`.
7. **Persiste** `Suscripcion`:
   - `estado = "pendiente"`, `fecha_inicio = now`, `fecha_fin = now + plan.duracion_dias`, `renovacion_automatica = True`, `proveedor_pago = "mercadopago"`, `external_subscription_id = preference_id`.
8. **Respuesta** → `{ init_point, preference_id }` (`CrearPreferenciaResponse`).

---

## 4. Webhook de pagos

Endpoint: **`POST /api/pagos/webhook`** (no requiere token; MercadoPago lo invoca con un formulario).

1. Lee `topic` y `id` desde el **form** o los **query params**.
2. Solo si `topic == "payment"` y hay `payment_id`:
   - `sdk.payment().get(int(payment_id))`.
   - Si `status == 200` y `payment["status"] == "approved"`:
     - Toma `external_reference` (`"id_negocio:id_plan"`), lo parte por `:`, y llama a `procesar_pago_exitoso(db, negocio_id, plan_id, preference_id)`.
3. **Errores**: cualquier excepción se loguea y **no** se propaga (el webhook siempre responde `{"status": "ok"}` → HTTP 200). Esto evita reintentos infinitos de MercadoPago pero también puede perder notificaciones fallidas.

---

## 5. Procesamiento del pago aprobado (`procesar_pago_exitoso`)

1. `Plan` debe existir → 404.
2. Busca la suscripción a confirmar:
   - primero por `external_subscription_id == preference_id` (misma preferencia);
   - si no, **fallback** a la `pendiente` más reciente del negocio.
3. Si existe:
   - Cancela las **otras** `pendiente` del negocio.
   - Cancela las **otras** `activa` del negocio.
   - Si era `activa`: rellena/extiende desde `fecha_fin` vigente (acumulación) o desde ahora si venció → `fecha_fin = base + plan.duracion_dias`.
   - Si estaba en otro estado: pasa a `activa`, actualiza `id_plan`, fechas desde ahora, `renovacion_automatica`, `proveedor_pago`.
4. Si no existía: **crea** una `activa` (fechas desde ahora, `external_subscription_id = preference_id`).
5. `commit` + `refresh` → devuelve la `Suscripcion`.

Este es el punto que garantiza **una sola suscripción activa** por negocio (ver [SUSCRIPCIONES.md](./SUSCRIPCIONES.md) §7).

---

## 6. Otros endpoints de pagos/suscripción (`pago_router`)

| Endpoint | Auth | Lógica |
|---|---|---|
| `GET /api/pagos/suscripcion/actual` | dueño | `obtener_suscripcion_actual` → la más reciente por `fecha_inicio DESC` (de cualquier estado) |
| `POST /api/pagos/suscripcion/{id}/cancelar` | dueño | solo `activa`/`pendiente`; 400 si otro estado; marca `cancelada` |
| `PUT /api/pagos/suscripcion/{id}/renovacion-automatica` | dueño | setea el booleano |

---

## 7. Errores posibles (back-end)

| Escenario | HTTP |
|---|---|
| Plan inexistente o inactivo | 404 |
| Error de red/API de MercadoPago al crear preferencia | 502 |
| MercadoPago responde `status` distinto de 200/201 | 502 |
| MercadoPago no devuelve `id` de preferencia | 502 |
| Suscripción a cancelar no encontrada | 404 |
| Cancelar una suscripción `cancelada` | 400 |
| Sin token/negocio en `crear-preferencia` y suscripción endpoints | 401/404 (vía `get_current_negocio`) |

---

## 8. Observaciones reales (sin inventar)

- El `external_subscription_id` guarda el **id de preferencia** (no un id de suscripción recurrente de MP): el "recurrente" es conceptual (`renovacion_automatica` + duración), no un mecanismo de cobro automático de MercadoPago en este request/response.
- El flujo de **confirmación real es el webhook** con `status approved`; los `back_urls` redirigen al frontend pero la activación la hace el webhook sobre `external_reference`.
- `date_of_expiration` (24 h) y `auto_return` son los únicos parámetros de la preferencia fijados por el backend; **no** se usan tickets, multiline ni `binary_mode`.
- **No hay secrets en este documento**; la credencial `MERCADOPAGO_ACCESS_TOKEN` se referencia únicamente por nombre.