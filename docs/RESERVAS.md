# Reservas (Turnos) — Backend TurnoGo

Documentación de la lógica de negocio de **reserva de turnos**, verificada contra `app/services/turno_service.py`, `app/routers/turno_router.py`, `app/schemas/appointment_schema.py`, `app/models/turnos.py`, `horarios_negocio_service.py`, `cliente_service.py`, `plan_service.py` y `scheduler_wsp.py`.

Se documenta **solo** lo que hace el backend. Si una regla de la interfaz (p. ej. qué horarios se deshabilitan en el calendario) no existe en este repo, no se atribuye al backend.

---

## 1. Vista general del flujo

1. El **dueño** configura el negocio: servicios (con duración), empleados y **horarios de atención**.
2. Se crea el **cliente** por teléfono (`obtener_o_crear_cliente`, get-or-create por teléfono UNIQUE).
3. Se crea el **turno** `POST /api/turnos/` indicando negocio, cliente, servicio, `fecha_hora_inicio` y empleado opcional.
4. El backend valida: servicio/negocio activos → límite plan Free → rango horario → superposición → cliente existente.
5. El turno se crea siempre en estado **CONFIRMADO** y se envía email de confirmación con QR (en background, solo si el cliente tiene email).
6. El dueño gestiona el estado posterior mediante `PUT /api/turnos/{id}/estado` (confirmación implícita ya hecha en la creación, cancelación, completado, no asistió).

> IMPORTANTE: `PENDIENTE` (1) es un estado **definido** en el catálogo y en la máquina de transiciones, pero **ningún flujo actual lo asigna**: la creación fija `CONFIRMADO` directamente. El campo `servicio.requiere_aprobacion` existe en el modelo/schema pero **no** condiciona el estado inicial.

---

## 2. Endpoints (routers)

Todos en `app/routers/turno_router.py`, montado en `/api` (`app/main.py:50`).

| Método | Ruta | Auth | Función de servicio | Descripción |
|---|---|---|---|---|
| GET | `/api/turnos/por-rango` | no | `listar_turnos_por_negocio_y_rango` | Turnos que **solapan** `[desde, hasta)`; filtro opcional `id_empleado`; ordenados por `fecha_hora_inicio` asc. Valida `hasta > desde` (400). |
| GET | `/api/turnos/` | no | `listar_turnos` | **Todos** los turnos de la base, sin filtro por negocio. |
| GET | `/api/turnos/{id}` | no | `obtener_turno_por_id` | Turno por id (404 si no existe). |
| POST | `/api/turnos/` | no | `crear_turno` | Crear reserva (201). |
| PUT | `/api/turnos/{id}` | no | `actualizar_turno` | Editar turno (incluye re-asignar fecha/servicio/empleado/negocio y opcionalmente estado). |
| DELETE | `/api/turnos/{id}` | no | `borrar_turno` | **Borrado físico** del turno (204). Sin chequear estado ni pertenencia. |
| PUT | `/api/turnos/{id}/estado` | **dueño** (`get_current_negocio`) | `cambiar_estado_turno` | Cambiar de estado validando transición y pertenencia (403 si el turno no es de tu negocio). |

> Nota: los endpoints de creación/consulta no requieren autenticación; solo el cambio de estado exige token de dueño.

---

## 3. Creación de un turno (`crear_turno`)

Entrada `TurnoCrear` (`appointment_schema.py:21`):

```
id_negocio: int            obligatorio
id_cliente: int            obligatorio
id_servicio: int           obligatorio
fecha_hora_inicio: datetime
id_empleado: int | None    opcional
```

### 3.1 Pasos y validaciones (en orden)

1. **Servicio y negocio activos** — `obtener_servicio_del_negocio`
   - El servicio debe existir, pertenecer al `id_negocio`, estar **activo**, y el **negocio activo**.
   - Si no → **404** `"Servicio no encontrado para el negocio indicado o negocio inactivo"`.
2. **Límite de plan Free** (solo si el negocio NO tiene la feature `turnos_ilimitados`, `plan_service.negocio_tiene_funcion`):
   - Cuenta turnos del negocio en la **fecha de inicio** (`func.date(fecha_hora_inicio)`) con estado **≠ CANCELADO**.
   - Si `contador >= LIMITE_TURNOS_DIA_FREE (10)` → **403**.
   - Las suscripciones con feature `turnos_ilimitados` ignoran este límite.
3. **Resolver `fecha_hora_fin`** — `_resolver_fecha_hora_fin`
   - Si no viene `fecha_hora_fin`, se calcula `fecha_hora_inicio + servicio.duracion_min`.
   - Se usa **`duracion_min`** (no `duracion_max`).
4. **Rango válido** — `validar_rango_horario`: si `fin <= inicio` → **400**.
5. **Empleado del negocio** — `validar_empleado_del_negocio` (solo si `id_empleado` provisto):
   - Debe existir, pertenecer al negocio y estar **activo** → si no, **400** `"Empleado no encontrado para el negocio indicado"`.
6. **Dentro del horario de atención** — `validar_turno_dentro_del_horario` (ver §4).
7. **Sin superposición** — `hay_superposicion` (ver §5) → **409**.
8. **Cliente existe** — sí o sí (aquí no se crea el cliente) → **404** `"El cliente especificado no existe."`
9. **Estado inicial** = **CONFIRMADO** (2) — `_resolver_estado_inicial` siempre devuelve `CONFIRMADO`.
10. Insert + `commit` + `refresh`. Luego, en **background** (`BackgroundTasks`, no bloquea la respuesta 201): email de confirmación con QR si `cliente.email`.
11. Ante `IntegrityError`: `rollback`. Si el mensaje contiene `ex_turno_no_solapa_por_empleado` → **409** (detalle de solapamiento); cualquier otra falla de integridad → **400** con el texto del error.

### 3.2 Respuesta y modelo expuesto

`TurnoResponse` (`appointment_schema.py:76`) anida: `cliente`, `empleado` (opcional), `servicio`, `estado` (catálogo `nombre_estado`), además de `fecha_hora_inicio`, `fecha_hora_fin`, `rechazado_motivo`, `created_at`, `updated_at`.

---

## 4. Horarios del negocio y validación de horario

### 4.1 Definición (`horarios_negocio_service.py`)

- Cada franja es `HorarioNegocio(id_negocio, dia_semana 0..6=weekday, hora_apertura, hora_cierre)`.
- Al **crear/actualizar** (`crear_horarios` / `actualizar_horarios`) se valida:
  - `hora_apertura != hora_cierre` (400).
  - Máximo **2 franjas por día** (`MAX_FRANJAS_POR_DIA = 2`) (400).
  - Las franjas de un mismo día no pueden **superponerse** (400). Para compararlas, el cierre que cruza medianoche se normaliza sumando 1440 min (`_normalized_end_min`).
- `actuarizar_horarios` **borra todos los horarios del negocio y los recrea** (delete + insert).
- `obtener_horarios_por_negocio` devuelve **404** si el negocio no tiene horarios. **No existe horario por defecto.**
- `eliminar_horarios` borra **todos** los horarios del negocio (404 si no hay).

### 4.2 Cómo valida el turno estar dentro del horario (`validar_turno_dentro_del_horario`)

- Si el negocio **no tiene horarios** → la validación se **omite** (el turno se acepta).
- Días: el turno se compara contra `dias_semana_validos = {inicio.weekday(), inicio.isoweekday()}` (unión de ambos). Es decir, la franja se considera válida si su `dia_semana` coincide con **cualquiera** de los dos valores.
- Franja que **no cruza medianoche**: válido si `apertura <= hora_inicio AND hora_fin <= cierre`.
- Franja que **cruza medianoche** (`cierre <= apertura`): válido si `(hora_inicio >= apertura OR hora_inicio <= cierre)` **y** `(hora_fin >= apertura OR hora_fin <= cierre)`.
- Si ninguna franja acepta → **400** `"El turno está fuera del horario de atención del negocio"`.

---

## 5. Disponibilidad: superposición

### 5.1 Verificación en aplicación (`hay_superposicion`)

Se considera que existe solapamiento si hay un turno en la **misma tabla**, del **mismo negocio**, con:

```
Turno.fecha_hora_inicio < fin  AND  Turno.fecha_hora_fin > inicio
```

- Si `id_empleado` provisto → filtra por ese empleado.
- **No filtra por estado**: los turnos CANCELADO también cuentan como ocupación para esta verificación.
- `excluir_turno_id` permite ignorar el propio turno (usado en edición).

### 5.2 Reglas resultantes (reglas reales del backend)

- **Sin empleado** (`id_empleado = None`): el turno no debe solaparse con **ningún** turno del negocio, incluidos los que tienen empleado asignado.
- **Con empleado**: no debe solaparse con ningún turno de *ese* empleado en el negocio.
- Al fallar → **409** `"El empleado ya tiene un turno en ese horario"` (mensaje literal aunque no haya empleado indicado).

### 5.3 Protección a nivel base de datos (doble defensa)

La migración SQL crea el índice de **exclusión GiST** por empleado:

```
(id_empleado, tstzrange(fecha_hora_inicio, fecha_hora_fin, '[)'))
```

por lo que, ante una condición de carrera (dos peticiones simultáneas que pasan la validación en Python), la base rechaza el segundo insert. `crear_turno` captura ese `IntegrityError` y lo traduce a **409**. El caso sin empleado **no** tiene protección GiST (solo validación en aplicación).

---

## 6. Servicio, cliente y negocio

| Entidad | Rol en la reserva |
|---|---|
| **Servicio** | Define la **duración** (`duracion_min` usada para calcular `fecha_hora_fin`). Debe estar `activo` y pertenecer al negocio. `precio` se usa en estadísticas de facturación (turnos COMPLETADO), no al reservar. |
| **Cliente** | Debe **existir** al crear el turno (404 en caso contrario). Se identifica por teléfono **UNIQUE**. `obtener_o_crear_cliente` normaliza el teléfono (quita espacios y no-dígitos salvo `+`, mínimo **8 dígitos**, nombre y apellido obligatorios) y, si un cliente existente no tiene email, lo completa en el primer contacto. |
| **Negocio** | Debe estar `activo` (junto con el servicio). Sus horarios definen la ventana válida. Su suscripción/plan determina el límite diario y las features. `negocio.activo` se controla dentro de `obtener_servicio_del_negocio` (join + filtro). El email de confirmación usa `negocio.nombre`, `direccion` y `telefono` si están cargados. |

---

## 7. Fecha y hora

- `fecha_hora_inicio` y `fecha_hora_fin` se almacenan como `DateTime` (sin zona). 
- `fecha_hora_fin` es **opcional** en el modelo, pero en la creación **siempre** se resuelve (o explícita o `inicio + duracion_min`).
- `created_at` / `updated_at` se asignan en la creación con `datetime.now(UTC)`; `updated_at` se reactualiza en cada edición. El schema los expone como `Optional`.
- La comparación `por-rango` es de **solapamiento** (`inicio < hasta AND fin > desde`), por lo que un turno aparece en varios rangos que corta.
- `rechazado_motivo` se acepta libremente en creación (viene `None`/no set) y en edición no se valida; la validación de motivo existe solo en el cambio de estado a CANCELADO (ver [ESTADOS_TURNO.md](./ESTADOS_TURNO.md)).

---

## 8. Edición y borrado

### `actualizar_turno` (PUT `/api/turnos/{id}`)

`TurnoActualizar` permite: `id_negocio`, `id_cliente`, `id_servicio`, `id_estado`, `id_empleado`, `fecha_hora_inicio`, `fecha_hora_fin`, `rechazado_motivo` (todos opcionales).

- **404** si el turno no existe.
- Se recalculan `nuevo_id_negocio`, `nuevo_id_servicio`, `nuevo_id_empleado`, `nueva_fecha_inicio` fusionando con lo existente.
- `fecha_hora_fin` se recalcula si cambió servicio/negocio/fecha de inicio (o si se pasó explícita).
- Se revalidan: rango horario, empleado del negocio, dentro del horario, superposición **excluyendo el propio turno**.
- Si `id_estado` viene: se respeta la máquina de estados (`validar_transicion`) → **400** `"No se puede pasar del estado X al Y"` si no está permitida.
- **No** valida la existencia del cliente al cambiar `id_cliente` (a diferencia de la creación).
- `commit` + `refresh`; `IntegrityError` → `rollback` y mapeo como en creación.

### `borrar_turno` (DELETE)

- **404** si no existe.
- Borra físicamente (no soft delete) y hace `commit`. Cualquier excepción se traduce en **500** con el mensaje del error.
- No restringe por estado (se puede borrar un COMPLETADO o un CANCELADO).

---

## 9. Transacciones

Patrón uniforme: una operación = una transacción.

- Éxito → `db.commit()`; recupera el objeto con `db.refresh()`.
- `IntegrityError` → `db.rollback()`; si menciona el índice GiST se devuelve 409, si no, 400.
- `borrar_turno` usa `except Exception` → `rollback` → 500.
- `cambiar_estado_turno` hace `commit` antes de encolar el email de cancelación en background.

---

## 10. Notificaciones (emails + QR)

### Confirmación al crear (`send_booking_confirmation_email`, `email_service.py:165`)

- Se dispara **después** del commit, en background, **solo si el cliente tiene `email`**.
- Datos: negocio, servicio, empleado (si hubo), fecha (`%d/%m/%Y`), hora (`%H:%M`), dirección y teléfono del negocio.
- Adjunta un **QR PNG** (`qr_service.generar_qr_png_bytes`) que codifica la URL `FRONTEND_URL/dashboard/turnos?turno={id_turno}`.

### Cancelación al cambiar estado (`send_cancellation_email`, `email_service.py:104`)

- Se envía al pasar a CANCELADO desde un estado distinto, si el cliente tiene email **y** hay `rechazado_motivo` (ver [ESTADOS_TURNO.md](./ESTADOS_TURNO.md)).

---

## 11. Recordatorios (`scheduler_wsp.py`) — NO activos

- `start_scheduler()` existe y registraría un job **cada hora** con apscheduler, pero **no se invoca en `main.py`** (comentado en el docstring del módulo).
- `obtener_turnos_para_recordatorio`: turnos de la franja del día siguiente (hora exacta `datetime.now() + 1 día`, redondeado a la hora) con `recordatorio_enviado == False`, de negocios con la feature `recordatorio_email`/`recordatorio_whatsapp` activa y no vencida.
- `verificar_y_enviar_recordatorios` marca `recordatorio_enviado = True` (el envío real por WhatsApp queda como TODO; los emails de recordatorio tampoco están conectados).

---

## 12. Reglas que NO están en el backend

Para evitar atribuciones incorrectas:

- **No hay endpoint de "disponibilidad"/slots**: el backend no expone qué horarios están libres; solo devuelve los turnos **ocupados** (`GET /api/turnos/por-rango`) y las franjas de atención (`GET /api/horarios/{id_negocio}`).
- La **selección de slots libres**, el bloqueo previo de frases y cualquier regla visual de agenda corresponden a la capa frontend (fuera de este repo).
- No existe estado automático "expirado"/"vencido": un turno pasado sigue con el estado que tenga hasta que el dueño lo cambie.