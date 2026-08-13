# Negocios — Backend TurnoGo

Documentación del módulo de **negocios**, verificada contra `app/models/negocio.py`, `app/models/categoria.py`, `app/models/negocio_imagen.py`, `app/schemas/negocio_schema.py`, `app/services/negocio_service.py`, `app/routers/negocio_router.py` y su uso de `plan_service`/`mapbox_service`.

---

## 1. Modelos

### `Negocio` (tabla `negocio`)
`app/models/negocio.py` — PK `id_negocio`.

| Columna | Tipo | Null | Default | Norte |
|---|---|---|---|---|
| `id_negocio` | Integer | no | — | **PK** index |
| `usuario_id` | Integer | no | — | **FK** `usuarios.id_us` (`ondelete=CASCADE`), **UNIQUE** (1 negocio por usuario) |
| `nombre` | String(150) | no | — | |
| `wsp` | String(20) | no | — | WhatsApp |
| `telefono` | String(20) | sí | — | |
| `direccion` | String(200) | no | — | |
| `ciudad` | String(100) | no | — | |
| `id_localidad` | Integer | sí | — | **FK** `localidades.id_localidad` (`ondelete=SET NULL`) |
| `id_provincia` | Integer | sí | — | **FK** `provincia.id_provincia` (`ondelete=SET NULL`) |
| `ig_url` | String(200) | sí | — | Instagram |
| `slug` | String(150) | no | — | **UNIQUE** index |
| `logo` | String(255) | sí | — | URL |
| `descripcion` | String(1000) | sí | — | |
| `activo` | Boolean | no | `True` | soft delete |
| `creado_at` | DateTime | no | `datetime.now` | |
| `id_categoria` | Integer | no | — | **FK** `categorias.id_categoria` |
| `latitud` / `longitud` | Float | sí | — | geocodificación (Mapbox) |

**Relaciones** (todas con `back_populates`, `cascade="all, delete-orphan"`, `passive_deletes=True`): `usuario`, `categoria`, `turnos`, `servicios`, `empleados`, `horarios`, `imagenes`, `suscripciones`.

### Modelos relacionados
- `Categoria` (tabla `categorias`, `app/models/categoria.py`): `id_categoria` PK, `nombre` UNIQUE, `icono` String(500), `descripcion` String(255), `created_at`; relación `negocios` 1—N.
- `NegocioImagen` (tabla `negocio_imagen`, `app/models/negocio_imagen.py`): `id_imagen` PK, `id_negocio` FK + index, `url` String(500), `es_portada` bool (la primera imagen de la lista es portada), `orden` int.
- `Provincia` / `Localidad` (`app/models/provincia.py`, `app/models/localidad.py`): FK `localidades.id_provincia` → `provincia` (sin `relationship` en el ORM).

---

## 2. Schemas (`app/schemas/negocio_schema.py`)

| Clase | Campos relevantes |
|---|---|
| `NegocioBase` | `nombre`, `id_categoria`, `wsp`, `telefono`, `direccion`, `ciudad`, `id_localidad`, `id_provincia`, `ig_url`, `logo`, `descripcion=""`, `activo=True` |
| `NegocioCreate` | + `usuario_id: int | None` |
| `NegocioImagenResponse` | `id_imagen`, `url`, `es_portada`, `orden` |
| `NegocioListResponse` | + `slug`, `latitud`, `longitud`, `categoria: CategoriaResponse`, `horarios: list[HorarioNegocioResponse]`, `tiene_mapa: bool` |
| `NegocioResponse` | `NegocioListResponse` + `imagenes` |
| `NegocioCompleteCreate` | `NegocioCreate` + `imagenes: list[str]`, `servicios: list[ServicioCreateNested]`, `empleados: list[EmpleadoCreate]`, `horarios: list[HorarioNegocioCreate]` |
| `NegocioCompleteResponse` | `NegocioResponse` + `servicios`, `empleados`, `horarios` |
| `NegocioUpdate` | todos opcionales (incluye `imagenes`, `id_categoria`, localidad/provincia, `activo`) |
| `DuenioResponse` | `nombre`, `email` |
| `NegocioAdminResponse` | datos del negocio + `duenio: DuenioResponse` |
| `NegocioMapaResponse` | `id_negocio`, `nombre`, `latitud`, `longitud` |

---

## 3. Endpoints (`app/routers/negocio_router.py`, `prefix="/negocios"`)

| Endpoint | Función de servicio | Auth | Detalle |
|---|---|---|---|
| `POST /api/negocios/admin/rebuild-data` | `backfill_negocios` | no | geocodifica negocios sin coordenadas |
| `GET /api/negocios/mapa` | `obtener_negocios_mapa` | no | solo negocios con feature `mapa_ubicacion` |
| `GET /api/negocios/` | `listar_negocios` | no | solo `activo == True` |
| `GET /api/negocios/admin` | `listar_negocios_admin` | no | con dueño |
| `GET /api/negocios/me` | `obtener_negocio_por_usuario` | **sí** (`get_current_user`) | 404 si el usuario no tiene negocio |
| `POST /api/negocios/` | `crear_negocio_completo` | **sí** | asigna `usuario_id = current_user.id_us`; 400 si falta categoría |
| `POST /api/negocios/complete` | (alias de `POST /`) | — | `include_in_schema=False` |
| `GET /api/negocios/slug/{slug}` | `obtener_negocio_por_slug` | no | solo activos |
| `GET /api/negocios/{negocio_id}` | `obtener_negocio_publico_por_id` | no | solo activos |
| `PUT /api/negocios/{negocio_id}` | `actualizar_negocio` | **sí** | dueño **o** admin |
| `DELETE /api/negocios/{negocio_id}` | `eliminar_negocio` | **sí** | **solo admin**; soft delete |
| `POST /api/negocios/backfill-coordenadas` | `backfill_negocios` | no | |

---

## 4. Servicios (`app/services/negocio_service.py`)

### Lecturas
- `obtener_negocios_mapa`: distinct sobre negocios con `latitud`/`longitud` no nulas, `activo`, suscripción `activa` no vencida **y** `PlanFeature.feature_key == "mapa_ubicacion"` (joins a `Suscripcion`, `Plan`, `PlanFeature`).
- `listar_negocios`: solo `activo == True`.
- `listar_negocios_admin`: todos con `joinedload(categoria, usuario)` → `NegocioAdminResponse` (dueño = `usuario_us`/`email_us`).
- `obtener_negocio_por_id`: con `joinedload(categoria)`.
- `obtener_negocio_publico_por_id`: solo activo, con `selectinload(horarios, imagenes)` y `tiene_mapa = negocio_tiene_funcion("mapa_ubicacion")`.
- `obtener_negocio_por_usuario`: por `usuario_id`, 404 si no existe.
- `obtener_negocio_por_slug`: solo activo, misma carga que público por id + `tiene_mapa`.

### Slug
- `generar_slug`: `nombre.lower()` → espacios a `-` → elimina todo excepto `[a-z0-9-]`.
- `generar_slug_unico`: si el slug ya existe agrega sufijos `-1`, `-2`, … hasta encontrar uno libre.

### Creación (`crear_negocio_completo`)
1. 400 si falta `usuario_id` o el usuario no existe.
2. 400 si falta `id_categoria` o la categoría no existe; 400 si `id_localidad`/`id_provincia` enviados no existen.
3. **Geocodificación** Mapbox (`obtener_coordenadas`) con dirección + ciudad (localidad) + provincia; errores se loguean y se continúa sin coordenadas.
4. Genera `slug` único.
5. Guarda negocio y luego, en la misma transacción (`flush` + `commit`): `NegocioImagen` (portada = índice 0), `Servicio`, `Empleado` y `HorarioNegocio` a partir de los arrays anidados.
6. Error → `rollback` → **500** `"Error al crear el negocio"`.

### Actualización (`actualizar_negocio`)
- 404 si no existe; **403 si no es el dueño** (`negocio.usuario_id != current_user.id_us`) **y** `role != "admin"`.
- `ALLOWED_FIELDS` filtra qué columnas pueden escribirse.
- `imagenes`: si se envía el campo, requiere la feature **`imagenes_personalizadas`** → si no: **403** `"Tu plan actual no incluye imágenes personalizadas..."`; se reemplaza la lista completa (portada = índice 0).
- Si cambió dirección o ciudad → se vuelve a geocodificar.

### Eliminación (`eliminar_negocio`)
- **Solo `role == "admin"`**, 403 si no; 404 si no existe; **soft delete** (`activo = False`).

### `backfill_negocios`
- Recorre todos los negocios sin coordenadas y las obtiene desde Mapbox (usando localidad/provincia cuando existen); no falla si el negocio ya no es activo (los considera todos).

---

## 5. Validaciones / permisos (resumen)

| Operación | Requisito |
|---|---|
| Ver listado/mapa/público/slug | público |
| `GET /me` | usuario autenticado |
| Crear | usuario autenticado (el negocio se ata a su `id_us`); categoría obligatoria y válida |
| Actualizar | dueño del negocio o rol `admin`; `imagenes` exige feature VIP |
| Eliminar | rol `admin` |

---

## 6. Flujo de datos

```
Frontend → POST /api/negocios/  (NegocioCompleteCreate)
  → valida usuario/categoría/localidad/provincia
  → Mapbox (coords)
  → slug único
  → crea Negocio + imagenes + servicios + empleados + horarios (1 commit)

Lecturas públicas → GET /slug/{slug} | GET /{id}  → NegocioResponse con categoria/horarios/imagenes + tiene_mapa

Admin → GET /admin (con dueño) | PUT|DELETE (permisos por rol)
```

---

## 7. Cómo se relaciona con los turnos

- El **negocio** es el contenedor lógico de todo el sistema de reservas: `turno.id_negocio` → `negocio.id_negocio` (FK), y `Negocio.turnos` es la relación 1—N.
- Para **crear un turno** el backend exige que el negocio (y el servicio) estén **activos**: `turno_service.obtener_servicio_del_negocio` hace `join(Negocio ...) .filter(Servicio.id_negocio==..., Negocio.activo.is_(True))`.
- `negocio.activo` marca alta/baja del negocio en el comercio público: los turnos no se pueden crear sobre un negocio inactivo, y los listados públicos lo filtran.
- Las **features del plan** del negocio condicionan la experiencia: `mapa_ubicacion` (mapa + `tiene_mapa`), `imagenes_personalizadas` (galería) y `turnos_ilimitados` (quita el límite de 10 turnos/día del plan Free) — esta última usada directamente por `turno_service.crear_turno`.
- El **slug** es la identidad pública del negocio para que el cliente llegue a la página de reserva; el email de confirmación incluye `nombre`, `direccion` y `telefono` del negocio.
- `GET /api/negocios/me` + `GET /auth/me` son la vía del dueño para operar su agenda (`GET /api/turnos/por-rango`) y cambiar estados (`PUT /api/turnos/{id}/estado`, protegido con `get_current_negocio`).