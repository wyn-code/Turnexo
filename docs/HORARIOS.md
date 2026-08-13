# Horarios del negocio — Backend TurnoGo

Documentación del módulo de **horarios de atención**, verificada contra `app/models/horarios_negocio.py`, `app/schemas/horarios_negocio_schema.py`, `app/services/horarios_negocio_service.py` y `app/routers/horarios_negocio_router.py`, más su uso en `turno_service.validar_turno_dentro_del_horario` y `estadistica_service`.

---

## 1. Modelo `HorarioNegocio` (tabla `horarios_negocio`)

`app/models/horarios_negocio.py` — PK `id_horarios_negocio`.

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `id_horarios_negocio` | Integer | no | **PK** index |
| `id_negocio` | Integer | no | **FK** `negocio.id_negocio` (`ondelete=CASCADE`) |
| `dia_semana` | Integer | no | día de la semana (`weekday()`: 0 = lunes … 6 = domingo) |
| `hora_apertura` | Time | no | |
| `hora_cierre` | Time | no | puede indicar cierre al día siguiente |

**Relación:** `negocio` (← `Negocio.horarios`).

> Una franja cuyos `hora_cierre <= hora_apertura` representa un horario que **cruza la medianoche** (p. ej. 22:00 → 02:00).

---

## 2. Schemas (`app/schemas/horarios_negocio_schema.py`)

| Clase | Campos |
|---|---|
| `HorarioNegocioCreate` | `dia_semana: int`, `hora_apertura: time`, `hora_cierre: time` |
| `HorarioNegocioResponse` | `HorarioNegocioCreate` + `id_horarios_negocio`, `id_negocio` |

Sin validaciones Pydantic adicionales: las reglas viven en el servicio.

---

## 3. Endpoints (`app/routers/horarios_negocio_router.py`, `prefix="/horarios"`)

| Endpoint | Función de servicio | Auth |
|---|---|---|
| `POST /api/horarios/{id_negocio}` | `crear_horarios` | no |
| `GET /api/horarios/{id_negocio}` | `obtener_horarios_por_negocio` | no |
| `PUT /api/horarios/{id_negocio}` | `actualizar_horarios` | no |
| `DELETE /api/horarios/{id_negocio}` | `eliminar_horarios` | no |

> **Hecho**: ninguno de estos endpoints exige autenticación ni verifica la titularidad del negocio. Reciben `id_negocio` como parte de la ruta.

---

## 4. Servicio (`app/services/horarios_negocio_service.py`)

Constantes/auxiliares:

- `MAX_FRANJAS_POR_DIA = 2`
- `_time_to_min(t)` → minutos desde las 00:00.
- `_normalized_end_min(apertura, cierre)` → cierre + 1440 min si `cierre <= apertura` (normalización de franjas que cruzan medianoche).
- `_validar_horarios(horarios, id_negocio_str)` — validaciones:

### Reglas de validación (`_validar_horarios`)
1. En **cada** franja: `hora_apertura != hora_cierre` → si no, **400**.
2. **Máximo 2 franjas por día** (`MAX_FRANJAS_POR_DIA`) agrupando por `dia_semana` → **400** si se supera.
3. Las franjas de un **mismo día** no pueden superponerse: se ordenan por apertura y se compara con el cierre normalizado (`_normalized_end_min`) → **400** `"Las franjas horarias del día {dia} se superponen"`.

### Operaciones
| Función | Lógica |
|---|---|
| `crear_horarios` | valida; inserta todos los `HorarioNegocio` del `id_negocio`; `commit` → `{"message": "Horarios guardados correctamente"}` |
| `obtener_horarios_por_negocio` | lista por `id_negocio`; **404** si no hay horarios |
| `actualizar_horarios` | **404** si no existen; valida; borra todos y recrea (delete + inserts) en una transacción → mensaje de éxito |
| `eliminar_horarios` | **404** si no hay; borra todos → mensaje de éxito |

---

## 5. Reglas de negocio

- **Reemplazo**: mantener los horarios de un negocio = `PUT` completo (no hay edición puntual de una franja).
- **Ausencia de horarios** ≠ error de negocio: un negocio **sin horarios** es válido y la validación de turnos simplemente se **omite** (ver §7).
- **Cruce de medianoche** es una operación de primer nivel (no un caso límite): `_validar_horarios`, `validar_turno_dentro_del_horario` y la métrica de ocupación lo contemplan.

---

## 6. Flujo de datos

```
POST/PUT/DELETE /api/horarios/{id_negocio} → horarios_negocio_router (sin auth)
  → horarios_negocio_service
      _validar_horarios (400 en fallos)
      → INSERT (o DELETE+INSERT en actualizar) → commit

GET /api/horarios/{id_negocio} → lista o 404
```

---

## 7. Cómo se relaciona con los turnos

- `turno_service.validar_turno_dentro_del_horario` (llamada por `crear_turno` y `actualizar_turno`) usa **exactamente** estas franjas:
  - Si el negocio **no tiene horarios** → la validación se omite (el turno se acepta).
  - Compara `dias_semana_validos = {inicio.weekday(), inicio.isoweekday()}` contra `horario.dia_semana`.
  - Franja normal (`apertura <= cierre`): válida si `apertura <= hora_inicio AND hora_fin <= cierre`.
  - Franja que cruza medianoche (`cierre <= apertura`): válida si `(hora >= apertura OR hora <= cierre)` para inicio **y** para fin.
  - Falla → **400** `"El turno está fuera del horario de atención del negocio"`.
- `estadistica_service._total_available_slots` también los consume para calcular **ocupación** (suma minutos por día y divide en slots de 30 min; no considera el cruce de medianoche correctamente — resta `cierre - apertura` sin normalizar).
- Las franjas se crean/editan junto con el negocio cuando se usa `NegocioCompleteCreate.horarios` (ver [NEGOCIOS.md](./NEGOCIOS.md)).