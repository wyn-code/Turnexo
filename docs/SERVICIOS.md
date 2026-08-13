# Servicios — Backend TurnoGo

Documentación del módulo de **servicios**, verificada contra `app/models/servicio.py`, `app/schemas/servicio_schema.py`, `app/services/servicio_service.py` y `app/routers/servicio_router.py`.

---

## 1. Modelo `Servicio` (tabla `servicio`)

`app/models/servicio.py` — PK `id_servicio`.

| Columna | Tipo | Null | Default | Notas |
|---|---|---|---|---|
| `id_servicio` | Integer | no | — | **PK** index |
| `id_negocio` | Integer | no | — | **FK** `negocio.id_negocio` (`ondelete=CASCADE`) |
| `nombre_servicio` | String(30) | no | — | |
| `precio` | Float | no | — | |
| `requiere_aprobacion` | Boolean | sí | — | + index; ver §4 |
| `duracion_min` | Integer | no | — | minutos |
| `duracion_max` | Integer | no | — | minutos |
| `activo` | Boolean | no | — | soft delete (en el ORM **no** tiene default) |

**Relaciones:** `negocio` (← `Negocio.servicios`, `back_populates`); `turnos` (→ `Turno`, `back_populates="servicio"`, `passive_deletes=True`).

---

## 2. Schemas (`app/schemas/servicio_schema.py`)

| Clase | Campos |
|---|---|
| `ServicioBase` | `nombre_servicio: str`, `precio: float`, `requiere_aprobacion: bool = False`, `duracion_min: int`, `duracion_max: int`, `activo: bool = True` |
| `ServicioUpdate` | todos opcionales (`nombre_servicio`, `precio`, `requiere_aprobacion`, `duracion_min`, `duracion_max`, `activo`) |
| `ServicioCreate` | `ServicioBase` + `id_negocio: int` |
| `ServicioCreateNested` | `ServicioBase` (sin `id_negocio`; el negocio lo aporta el contexto al crear el negocio completo) |
| `ServicioResponse` | `ServicioBase` + `id_servicio`, `id_negocio` (`from_attributes=True`) |

> No hay validación Pydantic de rango sobre `precio`, `duracion_min` o `duracion_max`: solo tipos. El CHECK `duracion_max >= duracion_min` está definido en la **migración SQL** (no en el modelo ORM).

---

## 3. Endpoints (`app/routers/servicio_router.py`, `prefix="/servicios"`)

| Endpoint | Función de servicio | Auth | Permiso de negocio |
|---|---|---|---|
| `GET /api/servicios/?id_negocio=` | `listar_servicios` | no | — |
| `POST /api/servicios/` | `crear_servicio` | **sí** (`get_current_user`) | `negocio.usuario_id == current_user.id_us` → si no, **403** |
| `PUT /api/servicios/{id_servicio}` | `actualizar_servicio` | **sí** | dueño del negocio del servicio → si no, **403** |
| `PATCH /api/servicios/{id_servicio}` | `toggle_servicio` | **sí** | dueño del negocio del servicio → **403** si no |
| `DELETE /api/servicios/{id_servicio}` | `eliminar_servicio` | **sí** | dueño del negocio del servicio → **403** si no |

- `GET` no requiere token.
- `PUT` y `PATCH` son redundantes para cambiar activación: `PATCH` hace toggle (`activo = not activo`), `DELETE` hace **borrado lógico** (`activo = False`).

---

## 4. Servicio (`app/services/servicio_service.py`)

| Función | Lógica |
|---|---|
| `listar_servicios` | todos; si `id_negocio` viene, filtra `Servicio.id_negocio == id_negocio` |
| `crear_servicio` | inserta `Servicio(**data.model_dump())` + `commit` (empuja la creación por el negocio ya validado en el router) |
| `actualizar_servicio` | 404 si no existe; aplica solo los campos enviados (`exclude_unset`) con `setattr` |
| `eliminar_servicio` | 404 si no existe; **`servicio.activo = False`** (soft) |
| `toggle_servicio` | 404 si no existe; `activo = not activo` |

---

## 5. Reglas de negocio / permisos

- **Titularidad**: crear/editar/toggle/eliminar un servicio exige que el negocio pertenezca al usuario autenticado (comparación `negocio.usuario_id == current_user.id_us` en el router). El `role admin` **no** se consulta aquí (a diferencia de negocio update/delete).
- **Soft delete**: no existe borrado físico de servicios; se desactivan con `activo=False`.
- **`requiere_aprobacion`**: es un campo **declarado** (modelo + schema, por defecto `False`) pero **no se usa** en ninguna lógica de turno (`turno_service._resolver_estado_inicial` solo devuelve `CONFIRMADO`). No inventar un flujo de "aprobación" en el backend.
- **Duración**: se define por servicio; `duracion_min` es la que consume la reserva.

---

## 6. Flujo de datos

```
GET/POST/PUT/PATCH/DELETE → servicio_router
  → (POST/PUT/PATCH/DELETE) get_current_user → valida propiedad del negocio (403)
  → servicio_service → query/insert/update {activo} → commit
```

---

## 7. Cómo se relaciona con los turnos

- La **duración** del servicio determina el bloqueo de agenda: `turno_service._resolver_fecha_hora_fin` calcula `fecha_hora_inicio + servicio.duracion_min` cuando el cliente no manda `fecha_hora_fin`.
- Para **reservar**, el servicio debe estar **activo** y pertenecer al negocio del turno (y el negocio activo): `turno_service.obtener_servicio_del_negocio` (404 en caso contrario).
- Los **turnos existentes** referencian al servicio por `turno.id_servicio` (FK con `ondelete=CASCADE`); `Servicio.turnos` es la relación inversa.
- El **precio** solo se usa para estadísticas de facturación (turnos COMPLETADO), no se cobra al reservar.
- `GET /api/servicios/?id_negocio=` es lo que consume el frontend para poblar el selector de servicio del alta de turno.