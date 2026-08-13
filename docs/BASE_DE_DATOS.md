# Base de datos — Backend TurnoGo

Documentación de la capa de persistencia: motor, conexión, SQLAlchemy, Supabase, sesiones, transacciones y características relevantes. Verificado contra el código real.

---

## 1. Motor y conexión

| Aspecto | Valor |
|---|---|
| Motor | **PostgreSQL** (Supabase, versión 17) |
| Driver | `psycopg2-binary` |
| Conexión | `app/db/database.py` → `DATABASE_URL = config('DB')` (variable de entorno vía `python-decouple`, configurada en `.env`) |
| Engine (pool) | `pool_pre_ping=True`, `pool_recycle=300`, `pool_size=5`, `max_overflow=10` |
| SessionLocal | `sessionmaker(autocommit=False, autoflush=False, bind=engine)` |
| Verificación | `SELECT 1` al importar el módulo (las `OperationalError` se ignoran de forma silenciosa) |

El app se conecta a la base **directamente con la cadena Postgres** del proyecto Supabase. No usa el cliente `supabase-py`: **no** se utiliza Supabase Auth (la sesión es JWT propia + 2FA OTP) ni Supabase Storage/Realtime.

## 2. SQLAlchemy

- **Estilo de mapeo**: modelos *declarativos* (`class Base(DeclarativeBase)` en `app/db/base.py`), todos en `app/models/`. Ver [MODELOS.md](./MODELOS.md).
- **API de consultas**: estilo *legacy* `db.query(Model).filter(...)`; agregaciones con `func` (`func.count`, `func.coalesce`, …); carga ansiosa con `joinedload`/`selectinload` en los servicios.
- **Nombres de tablas**: por `__tablename__` explícito (en general en singular/`snake_case`, p. ej. `negocio`, `servicio`, `estado_turno`).
- **Inyección de sesión**: dos generadores `get_db` equivalentes, `app/core/dependencies.py` y `app/db/session.py`, ambos registrados como dependencias de FastAPI y sobreescritos en los tests.
- **Tests** (`tests/conftest.py`): SQLite **en memoria** (`sqlite://`) con `StaticPool`, pragma de FKs activada, `Base.metadata.create_all`, rollback por test vía `dependency_overrides`.

## 3. Sesiones y transacciones

El patrón general en los *services* es **una sesión = una transacción**:

```python
db = next(get_db())          # dependencia FastAPI
try:
    # ... operaciones ...
    db.commit()              # confirmación explícita
    db.refresh(obj)
except IntegrityError:
    db.rollback()            # deshacer y fallar controlado
    raise HTTPException(status_code=409, ...)
finally:
    db.close()
```

- Cada endpoint recibe su sesión vía dependencia; al terminar se cierra (generador `get_db`).
- Los errores de integridad (duplicados, solapamiento de turnos por el índice GiST) se capturan con `IntegrityError` y se traducen a `409`. Otros casos derivan en `HTTPException` con `msj` consumible por el frontend.

## 4. Supabase

- **Hosting** de PostgreSQL y contenedor de los scripts SQL (`supabase/migrations/*.sql`).
- **Esquema**: `public`. Extensión usada: `btree_gist` (indispensable para el índice de exclusión de solapamiento de turnos).
- La **libertad por migración** se declara en SQL (DDL con FKs, `ON DELETE`), mientras que los **models** replican la estructura para el ORM. Puede existir divergencia no sincronizada entre ambos (p. ej. longitud de columnas `varchar(80)` en SQL vs `String(30)` en ORM, `servicio.duracion_max` nullable en SQL vs `not null` en ORM).
- `alembic` está **presente pero apenas como convención**: `alembic/versions/` contiene migraciones de solo definición, sin `alembic/env.py` ni `alembic.ini`, por lo que **no** se genera el historial automáticamente desde los modelos; el esquema real lo define Supabase.
- **Seeds**: `app/db/seeds/` rellena catálogos de arranque: `Categoria`, `EstadoTurno`, `Plan` (+ `PlanFeature`) y `Provincia`/`Localidad` (cargadas vía `georef`).

## 5. Características relevantes

1. **Integridad de solapamiento de turnos**: índice de **exclusión GiST** por empleado en `turno`
   `(id_empleado, tstzrange(fecha_hora_inicio, fecha_hora_fin, '[)'))`
   → la DB **rechaza** turnos que se solapan; además se valida en Python antes de intentar insertar.
2. **Cascadas**: `negocio` es la raíz; borrar un negocio elimina en cascada servicio, empleado, turnos, horarios, imágenes y suscripciones. `negocio.usuario_id` es **UNIQUE** (1:1 Usuario↔Negocio).
3. **Soft deletes**: `estado`/`activo` booleanos en `usuarios`, `negocios`, `servicio`, `empleado`; los listados filtran por activo en los services. No hay borrado físico en la mayoría de flujos.
4. **Fecha/hora**: `DateTime` (con `fecha_hora_inicio` del turno) y `Time` en franjas horarias; se calcula `fecha_hora_fin` por duración del servicio.
5. **Estados de turno**: catálogo `estado_turno` (FK) + máquina de transiciones en `core/estados_turno.py` (lógica de aplicación, la DB no la valida).
6. **Unicidad globales**: `usuarios.email_us` y `usuarios.usuario_us` únicos; `cliente.telefono` único (identidad para get-or-create); `categorias.nombre` único; `negocio.slug` único (URL pública).
7. **Límites de negocio (features)**: `plan_features` define qué puede hacer un negocio (`negocio_tiene_funcion`) y el vencimiento está en `suscripciones.fecha_fin`.
8. **Pagos** (MVP en desarrollo): flujo MercadoPago con `preferencia`; si no se confirma, la suscripción empieza en `pendiente` y la preferencia se cancela por webhook/fallback.

## 6. Diagrama ER completo

Generado **exclusivamente** a partir de los modelos reales de `app/models/`. Solo se incluyen relaciones presentes (FK en migraciones SQL + `relationship` en ORM; `localidades`↔`provincia` se muestra punteada, ya que existe FK pero **no** `relationship` en el ORM).

```mermaid
erDiagram
    usuario ||--o| negocio : "posee 1:1 (usuario_id UNIQUE)"
    categoria ||--o{ negocio : "id_categoria"
    negocio ||--o{ servicio : "id_negocio"
    negocio ||--o{ empleado : "id_negocio"
    negocio ||--o{ horarios_negocio : "id_negocio"
    negocio ||--o{ negocio_imagen : "id_negocio"
    negocio ||--o{ turno : "id_negocio"
    negocio ||--o{ suscripciones : "id_negocio"
    plan ||--o{ plan_features : "id_plan"
    plan ||--o{ suscripciones : "id_plan"
    cliente ||--o{ turno : "id_cliente"
    servicio ||--o{ turno : "id_servicio"
    empleado ||--o{ turno : "id_empleado (nullable)"
    estado_turno ||--o{ turno : "id_estado"
    provincia ||..o{ localidades : "id_provincia (FK sin relationship ORM)"

    usuario {
        int id_us PK
        varchar50 usuario_us UK
        varchar100 email_us UK
        varchar255 contrasena_us
        varchar20 role
        datetime created_at
        boolean estado
        boolean email_verified
        varchar255 verification_token
        datetime verification_token_expiration
        varchar255 reset_token
        datetime reset_token_expiration
        varchar10 otp_code
        datetime otp_expires_at
        datetime last_2fa_verified_at
        varchar20 auth_provider
    }
    negocio {
        int id_negocio PK
        int usuario_id FK,UK
        varchar150 nombre
        varchar20 wsp
        varchar20 telefono
        varchar200 direccion
        varchar100 ciudad
        int id_localidad FK
        int id_provincia FK
        varchar200 ig_url
        varchar150 slug UK
        varchar255 logo
        varchar1000 descripcion
        boolean activo
        datetime creado_at
        int id_categoria FK
        float latitud
        float longitud
    }
    categoria {
        int id_categoria PK
        varchar100 nombre UK
        varchar500 icono
        varchar255 descripcion
        datetime created_at
    }
    servicio {
        int id_servicio PK
        int id_negocio FK
        varchar30 nombre_servicio
        float precio
        boolean requiere_aprobacion
        int duracion_min
        int duracion_max
        boolean activo
    }
    empleado {
        int id_empleado PK
        varchar30 nombre
        varchar30 apellido
        varchar30 telefono UK
        boolean activo
        int id_negocio FK
    }
    horarios_negocio {
        int id_horarios_negocio PK
        int id_negocio FK
        int dia_semana
        time hora_apertura
        time hora_cierre
    }
    negocio_imagen {
        int id_imagen PK
        int id_negocio FK
        varchar500 url
        boolean es_portada
        int orden
    }
    turno {
        int id_turno PK
        int id_negocio FK
        int id_servicio FK
        int id_empleado FK
        int id_cliente FK
        int id_estado FK
        datetime fecha_hora_inicio
        datetime fecha_hora_fin
        text rechazado_motivo
        boolean recordatorio_enviado
        datetime created_at
        datetime updated_at
    }
    cliente {
        int id_cliente PK
        varchar30 telefono UK
        varchar30 nombre
        varchar30 apellido
        varchar100 email
        datetime created_at
    }
    estado_turno {
        smallint id_estado PK
        varchar100 nombre_estado
    }
    localidades {
        int id_localidad PK
        varchar100 nombre
        int id_provincia FK
    }
    provincia {
        int id_provincia PK
        varchar100 nombre
    }
    planes {
        int id_plan PK
        varchar100 nombre
        numeric precio
        int duracion_dias
        varchar500 descripcion
        boolean activo
    }
    plan_features {
        int id_feature PK
        int id_plan FK
        varchar100 feature_key
    }
    suscripciones {
        int id_suscripcion PK
        int id_negocio FK
        int id_plan FK
        varchar20 estado
        datetime fecha_inicio
        datetime fecha_fin
        boolean renovacion_automatica
        varchar50 proveedor_pago
        varchar150 external_subscription_id
    }
    metodo_pago {
        int id_metd PK
        varchar30 nombre_metd
        datetime created_at
    }
```

> `metodo_pago` se incluye por completo pero **no participa** en el diagrama de relaciones: ninguna tabla referencia su PK.