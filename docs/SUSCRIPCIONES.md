# Suscripciones y planes — Backend TurnoGo

Documentación del módulo de **planes/suscripciones/restricciones**, verificada contra `app/models/plan.py`, `app/models/plan_feature.py`, `app/models/suscripcion.py`, `app/services/plan_service.py`, `app/routers/plan_router.py`, `app/schemas/plan_schema.py`, `app/db/seeds/seed_planes.py` y los consumidores de features (`turno_service`, `empleado_service`, `negocio_service`, `scheduler_wsp`, `dependencies.require_feature`).

El flujo de cobro se documenta por separado en [PAGOS.md](./PAGOS.md).

---

## 1. Modelos

### `Plan` (tabla `planes`)
`app/models/plan.py` — PK `id_plan`.

| Columna | Tipo | Null | Default | Notas |
|---|---|---|---|---|
| `id_plan` | Integer | no | — | **PK** index |
| `nombre` | String(100) | no | — | |
| `precio` | Numeric | no | — | ARS |
| `duracion_dias` | Integer | no | — | |
| `descripcion` | String(500) | sí | — | |
| `activo` | Boolean | no | `True` | |

- Relación `funciones` 1—N → `PlanFeature` (`cascade="all, delete-orphan"`).
- Propiedad `feature_keys` → `[pf.feature_key for pf in self.funciones]`.

### `PlanFeature` (tabla `plan_features`)
`app/models/plan_feature.py` — PK `id_feature`; `id_plan` **FK** `planes.id_plan`; `feature_key` String(100).

### `Suscripcion` (tabla `suscripciones`)
`app/models/suscripcion.py` — PK `id_suscripcion`.

| Columna | Tipo | Null | Default | Notas |
|---|---|---|---|---|
| `id_negocio` | Integer | no | — | **FK** `negocio.id_negocio` (`ondelete=CASCADE`) |
| `id_plan` | Integer | no | — | **FK** `planes.id_plan` |
| `estado` | String(20) | no | `"activa"` | valores usados por el código: `activa`, `pendiente`, `cancelada` |
| `fecha_inicio` | DateTime | no | `datetime.now` | |
| `fecha_fin` | DateTime | no | — | |
| `renovacion_automatica` | Boolean | sí | `True` | |
| `proveedor_pago` | String(50) | sí | — | `"mercadopago"` |
| `external_subscription_id` | String(150) | sí | — | id de preferencia de MercadoPago |

Relaciones: `negocio` (← `Negocio.suscripciones`), `plan` (← `Plan.suscripciones`).

---

## 2. Planes sembrados (`app/db/seeds/seed_planes.py`)

`seed_planes()` corre `PLANES` solo si la tabla `planes` está vacía. Los planes reales:

| Plan | precio | duracion_dias | features |
|---|---|---|---|
| **Free** | 0 | 0 | *(ninguna)* |
| **Básico** | 4999 | 30 | `mapa_ubicacion` |
| **VIP** | 9999 | 30 | `mapa_ubicacion`, `imagenes_personalizadas`, `soporte_prioritario` |

> Está documentado como catálogo sembrado; sin embargo, las **restricciones** que se aplican en el código se firman por `feature_key` (ver §5), no por el nombre del plan. `obtener_funciones_negocio` devuelve las features de la **suscripción activa** (no del plan en sí).

---

## 3. Schemas (`app/schemas/plan_schema.py`)

| Clase | Campos |
|---|---|
| `PlanResponse` | `id_plan`, `nombre`, `precio`, `duracion_dias`, `descripcion`, `activo`, `feature_keys: list[str]` |
| `SuscripcionResponse` | `id_suscripcion`, `estado`, `fecha_inicio`, `fecha_fin`, `renovacion_automatica`, `plan: PlanResponse` (anidado) |
| `NegocioFuncionesResponse` | `id_negocio`, `plan: str | None`, `estado: str | None`, `fecha_fin: datetime | None`, `funciones: list[str]` |
| `CrearPreferenciaRequest` / `CrearPreferenciaResponse` | ver [PAGOS.md](./PAGOS.md) |
| `RenovacionAutomaticaRequest` | `renovacion_automatica: bool` |

---

## 4. Servicios (`app/services/plan_service.py`)

| Función | Lógica |
|---|---|
| `negocio_tiene_funcion(id_negocio, feature_key, db) -> bool` | `True` si existe una suscripción del negocio, `estado == "activa"`, `fecha_fin >= datetime.now()` y el plan tiene esa `feature_key` (joins `Suscripcion → Plan → PlanFeature`). |
| `obtener_funciones_negocio(id_negocio, db) -> list[str]` | todas las `feature_key` de la suscripción activa vigente. |
| `obtener_suscripcion_activa(id_negocio, db) -> Suscripcion | None` | primera suscripción `activa` y vigente (con plan cargado). |

---

## 5. Restricciones reales por feature

Referencias encontradas en el código (features usadas):

| feature_key | Dónde se fuerza | Efecto si NO está activa |
|---|---|---|
| `turnos_ilimitados` | `turno_service.crear_turno` | límite de **10 turnos/día** (`LIMITE_TURNOS_DIA_FREE`) → **403** |
| `empleados_ilimitados` | `empleado_service.crear_empleado` | límite de **3 empleados** (`LIMITE_EMPLEADOS_FREE`) → **403** |
| `imagenes_personalizadas` | `negocio_service.actualizar_negocio` | al enviar `imagenes` → **403** |
| `mapa_ubicacion` | `negocio_service.obtener_negocios_mapa` y `tiene_mapa` | el negocio no aparece en el mapa / `tiene_mapa=False` |
| `recordatorio_email` / `recordatorio_whatsapp` | `scheduler_wsp.obtener_turnos_para_recordatorio` | el negocio no recibe recordatorios (módulo no activo) |
| `soporte_prioritario` | — (sin código de fuerza; solo label del plan VIP) | — |

> Existe además la dependencia genérica **`require_feature(feature_key)`** en `app/core/dependencies.py`: levanta **403** si el negocio del token no tiene la feature. Hasta el momento **no está montada en ningún endpoint** (verificable por búsqueda en routers).

---

## 6. Endpoints (`app/routers/plan_router.py`, `prefix="/planes"`)

| Endpoint | Auth | Lógica |
|---|---|---|
| `GET /api/planes/` | no | todos los planes **activos** con sus `funciones` (`selectinload`) → `PlanResponse` |
| `GET /api/planes/negocios/{id_negocio}/funciones` | no | 404 si el negocio no existe; `NegocioFuncionesResponse` con `plan`/`estado`/`fecha_fin` de `obtener_suscripcion_activa` y `funciones` de `obtener_funciones_negocio` |

---

## 7. Estados y reglas de "una sola suscripción activa"

Estados de `Suscripcion.estado` (strings usadas en `payment_service`): **`activa`**, **`pendiente`**, **`cancelada`**.

La lógica que evita más de una suscripción activa/pendiente por negocio está **implementada** en `app/services/payment_service.py` (nada de esto es declarativo en la BD):

1. **Al crear una preferencia** (`crear_preferencia_mp`):
   ```python
   db.query(Suscripcion).filter(
       Suscripcion.id_negocio == negocio.id_negocio,
       Suscripcion.estado == "pendiente",
   ).update({"estado": "cancelada"})
   ```
   → cualquier `pendiente` previa del negocio se vuelve `cancelada` antes de persistir la nueva. (Nótese que **no** toca las `activa` en este paso).

2. **Al confirmar el pago** (`procesar_pago_exitoso`):
   ```python
   # cancela OTRAS pendientes (si no es la que se está confirmando)
   ... estado == "pendiente", id_suscripcion != suscripcion.id_suscripcion → "cancelada"
   # cancela OTRAS activas
   ... estado == "activa", id_suscripcion != suscripcion.id_suscripcion → "cancelada"
   ```
   → deja como máximo **una** suscripción `activa` por negocio, y limpia las `pendiente` huérfanas.

3. **Lectura**:
   - `plan_service.obtener_suscripcion_activa` → una `activa` vigente (primera que encuentre).
   - `payment_service.obtener_suscripcion_actual` → la más reciente por `fecha_inicio DESC` (sin filtrar por estado).

> No hay constraint de unicidad en la base (p. ej. índice parcial sobre `id_negocio WHERE estado='activa'`): la "única activa" se garantiza por **lógica de servicio** en `procesar_pago_exitoso`/`crear_preferencia_mp`.

---

## 8. Consumo del frontend / flujo típico

```
GET /api/planes                                → lista de planes (precio, duracion_dias, feature_keys)
GET /api/planes/negocios/{id}/funciones        → plan actual + features habilitadas
GET /api/pagos/suscripcion/actual              → suscripción vigente / más reciente
POST /api/pagos/crear-preferencia              → inicia el pago (ver PAGOS.md)
```

**Relación con turnos:** las features `turnos_ilimitados` y `empleados_ilimitados` son las que habilitan a un negocio Free a escalar la cantidad de turnos diarios y empleados (ver §5).