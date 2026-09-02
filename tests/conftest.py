import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

os.environ["RATE_LIMIT_ENABLED"] = "false"

from app.db.base import Base
from app.core.dependencies import get_db as get_db_core
from app.db.session import get_db as get_db_session

SQLALCHEMY_DATABASE_URL = "sqlite://"

from sqlalchemy.pool import StaticPool

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

@pytest.fixture()
def setup_db():
    from app.models.negocio import Negocio
    from app.models.cliente import Cliente
    from app.models.turnos import Turno
    from app.models.servicio import Servicio
    from app.models.usuario import Usuario
    from app.models.empleado import Empleado
    from app.models.provincia import Provincia
    from app.models.localidad import Localidad
    from app.models.plan import Plan
    from app.models.plan_feature import PlanFeature
    from app.models.suscripcion import Suscripcion

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(setup_db): 
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def _mock_email_senders(monkeypatch):
    """Evita llamadas reales a Resend durante los tests."""
    import app.services.email_service as email_service
    import app.services.auth_service as auth_service

    for module in (email_service, auth_service):
        monkeypatch.setattr(
            module,
            "send_otp_email",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            module,
            "send_verification_email",
            lambda *args, **kwargs: None,
        )


from app.main import app 
from app.core.dependencies import get_db

@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    # Sobrescribimos AMBAS rutas posibles para asegurarnos de que atrape todo
    app.dependency_overrides[get_db_core] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()

@pytest.fixture()
def seed_data(db):
    from datetime import datetime, timezone
    from app.models.negocio import Negocio
    from app.models.servicio import Servicio
    from app.models.empleado import Empleado
    from app.models.usuario import Usuario
    from app.models.categoria import Categoria
    from app.models.estado_turno import EstadoTurno
    from app.core.security import get_password_hash

    _recent_2fa = datetime.now(timezone.utc).replace(tzinfo=None)

    usuario_1 = Usuario(
        id_us=1,
        usuario_us="testuser1",
        email_us="test1@test.com",
        contrasena_us=get_password_hash("Test1234567!"),
        email_verified=True,
        last_2fa_verified_at=_recent_2fa,
    )

    usuario_2 = Usuario(
        id_us=2,
        usuario_us="testuser2",
        email_us="test2@test.com",
        contrasena_us=get_password_hash("Test1234567!"),
        email_verified=True,
        last_2fa_verified_at=_recent_2fa,
    )

    db.add_all([usuario_1, usuario_2])
    # Puedes usar flush aquí si necesitas los IDs generados antes del commit final
    db.flush() 

    categoria_prueba = Categoria(nombre="Categoría Test")
    db.add(categoria_prueba)
    db.flush()

    estado_pendiente = EstadoTurno(id_estado=1, nombre_estado="Pendiente")
    db.add(estado_pendiente)
    db.flush()

    for eid, nombre in [(2, "Confirmado"), (3, "Completado"),
                        (4, "Cancelado"), (5, "No asistio"),
                        (6, "Asistio")]:
        db.add(EstadoTurno(id_estado=eid, nombre_estado=nombre))
    db.flush()

    negocio = Negocio(
        id_negocio=1,
        usuario_id=1,
        nombre="Test Negocio",
        id_categoria = 1,
        wsp="Test1234567!789",
        direccion="Test 123",
        ciudad="San Nicolas",
        activo=True,
        slug="test-negocio",
    )
    db.add(negocio)
    db.flush()

    servicio = Servicio(
        id_servicio=1,
        id_negocio=1,
        nombre_servicio="Corte",
        precio=1000,
        requiere_aprobacion=False,
        duracion_min=30,
        duracion_max=30,
        activo=True,
    )
    db.add(servicio)
    db.flush()

    empleado = Empleado(
        id_empleado=1,
        id_negocio=1,
        nombre="Juan",
        apellido="Perez",
        telefono="Test1234567!789",
        activo=True,
    )
    db.add(empleado)
    
    # --- LA CORRECCIÓN ESTÁ AQUÍ ---
    db.commit() 
    # -------------------------------

    return {
        "usuario_1": usuario_1,
        "usuario_2": usuario_2,
        "negocio": negocio,
        "servicio": servicio,
        "empleado": empleado,
        "estado_pendiente": estado_pendiente
    }
