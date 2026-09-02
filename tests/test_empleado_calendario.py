import re
from datetime import datetime, timedelta, timezone

import pytest

from sqlalchemy import event, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from tests.auth_helpers import obtener_token

from app.main import app
from app.db.base import Base
from app.db.session import get_db as get_db_session
from app.core.security import get_password_hash

from app.models.empleado import Empleado
from app.models.turnos import Turno
from app.models.cliente import Cliente
from app.models.negocio import Negocio
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.estado_turno import EstadoTurno

from icalendar import Calendar


# ============================================================================
# DATABASE
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture()
def setup_db():
    # Importar todos los modelos para que estén registrados en Base.metadata
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
def db_session(setup_db):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def db(db_session):
    yield db_session


@pytest.fixture(autouse=True)
def _mock_email_senders(monkeypatch):
    """Evita llamadas reales a Resend durante los tests."""

    import app.services.email_service as email_service
    import app.services.empleado_calendario_service as cal_service

    monkeypatch.setattr(
        email_service,
        "send_calendario_email",
        lambda *a, **k: None,
    )

    monkeypatch.setattr(
        cal_service,
        "send_calendario_email",
        lambda *a, **k: None,
    )


@pytest.fixture()
def client(db_session):
    from app.core.dependencies import get_db as get_db_core

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_core] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# HELPERS
# ============================================================================

def _crear_usuario_duenio(db, id_us=1, email="test1@test.com"):
    usuario = Usuario(
        id_us=id_us,
        usuario_us=email,
        email_us=email,
        contrasena_us=get_password_hash("Test1234567!"),
        email_verified=True,
        last_2fa_verified_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario


def _crear_negocio(db, usuario_id=1, id_negocio=1):
    categoria = Categoria(nombre=f"Cat Negocio {id_negocio}")
    db.add(categoria)
    db.flush()

    negocio = Negocio(
        id_negocio=id_negocio,
        usuario_id=usuario_id,
        nombre="Test Negocio",
        id_categoria=categoria.id_categoria,
        wsp="Test123456789",
        direccion="Test 123",
        ciudad="San Nicolas",
        activo=True,
        slug=f"test-negocio-{id_negocio}",
    )

    db.add(negocio)
    db.commit()
    db.refresh(negocio)

    return negocio


def _crear_servicio(db, id_negocio=1, id_servicio=1):
    categoria = Categoria(nombre=f"Cat Test {id_servicio}")
    db.add(categoria)
    db.flush()

    servicio = Servicio(
        id_servicio=id_servicio,
        id_negocio=id_negocio,
        nombre_servicio="Corte",
        precio=1000,
        requiere_aprobacion=False,
        duracion_min=30,
        duracion_max=30,
        activo=True,
    )

    db.add(servicio)
    db.commit()
    db.refresh(servicio)

    return servicio


def _crear_empleado(db, id_negocio=1, id_empleado=1):
    empleado = Empleado(
        id_empleado=id_empleado,
        id_negocio=id_negocio,
        nombre="Juan",
        apellido="Perez",
        telefono="123456789",
        activo=True,
    )

    db.add(empleado)
    db.commit()
    db.refresh(empleado)

    return empleado


def _crear_cliente(db, id_negocio=1, id_cliente=None):
    cliente = Cliente(
        nombre="Test",
        apellido="Client",
        telefono="123456789",
        email=f"test{id_cliente or 'x'}@test.com",
    )

    if id_cliente is not None:
        cliente.id_cliente = id_cliente

    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return cliente


def _crear_estado(db, id_estado, nombre="Test"):
    estado = (
        db.query(EstadoTurno)
        .filter(EstadoTurno.id_estado == id_estado)
        .first()
    )

    if not estado:
        estado = EstadoTurno(
            id_estado=id_estado,
            nombre_estado=nombre,
        )
        db.add(estado)
        db.commit()
        db.refresh(estado)

    return estado


def _crear_turno(
    db,
    id_empleado,
    id_cliente,
    id_servicio=1,
    id_negocio=1,
    id_estado=2,
    fecha_inicio_utc=None,
    fecha_fin_utc=None,
):
    """
    Crea un turno con fecha UTC.

    Si no se especifica fecha, usa ahora + 1 día.
    No fuerza id_turno para permitir múltiples turnos.
    """

    if fecha_inicio_utc is None:
        fecha_inicio_utc = datetime.now(timezone.utc) + timedelta(days=1)

    _crear_estado(db, id_estado)

    turno = Turno(
        id_negocio=id_negocio,
        id_cliente=id_cliente,
        id_servicio=id_servicio,
        id_empleado=id_empleado,
        id_estado=id_estado,
        fecha_hora_inicio=fecha_inicio_utc,
        fecha_hora_fin=fecha_fin_utc,
        rechazado_motivo=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(turno)
    db.commit()
    db.refresh(turno)

    return turno


def _crear_datos_calendario(db):
    """
    Crea el conjunto mínimo de datos necesarios para los tests.
    """

    usuario = _crear_usuario_duenio(db)

    negocio = _crear_negocio(
        db,
        usuario_id=usuario.id_us,
        id_negocio=1,
    )

    servicio = _crear_servicio(
        db,
        id_negocio=negocio.id_negocio,
        id_servicio=1,
    )

    empleado = _crear_empleado(
        db,
        id_negocio=negocio.id_negocio,
        id_empleado=1,
    )

    cliente = _crear_cliente(
        db,
        id_negocio=negocio.id_negocio,
        id_cliente=1,
    )

    return {
        "usuario": usuario,
        "negocio": negocio,
        "servicio": servicio,
        "empleado": empleado,
        "cliente": cliente,
    }


def _headers_duenio(client):
    return obtener_token(
        client,
        "test1@test.com",
        "Test1234567!",
    )


def _generar_calendario(client, headers, id_negocio=1, id_empleado=1):
    return client.post(
        f"/api/negocios/{id_negocio}/empleados/{id_empleado}/generar-calendario",
        headers=headers,
        json={"email": "juan.perez@test.com"},
    )


def _extraer_token(link):
    """
    Extrae el token de:
    /api/empleados/{token}/calendario.ics
    """

    match = re.search(
        r"/api/empleados/([^/]+)/calendario\.ics$",
        link,
    )

    assert match is not None, (
        f"El link no tiene el formato esperado: {link}"
    )

    return match.group(1)


def _fecha_manana_a_las_10_utc():
    """
    Devuelve un datetime UTC correspondiente a mañana a las 10:00 UTC.

    Se usa una fecha futura relativa a hoy para que el turno caiga dentro
    del rango que el feed incluye (fecha_hora_inicio >= ahora).
    """
    manana = datetime.now(timezone.utc) + timedelta(days=1)
    return manana.replace(
        hour=10,
        minute=0,
        second=0,
        microsecond=0,
    )


# ============================================================================
# TESTS
# ============================================================================

class TestEmpleadoCalendario:

    # ------------------------------------------------------------------------
    # 1. Generación y reutilización de token
    # ------------------------------------------------------------------------

    def test_generar_calendario_crea_token_y_email(
        self,
        client,
        db,
    ):
        """
        POST generar-calendario:
        - devuelve 201
        - genera token
        - devuelve link
        - actualiza calendario_enviado_at
        """

        _crear_datos_calendario(db)

        headers = _headers_duenio(client)

        response = _generar_calendario(
            client,
            headers,
        )

        assert response.status_code == 201

        data = response.json()

        assert data["id_empleado"] == 1
        assert data["calendario_link"] is not None
        assert data["calendario_link"].endswith(
            "/calendario.ics"
        )
        assert data["calendario_enviado_at"] is not None

        empleado = (
            db.query(Empleado)
            .filter(Empleado.id_empleado == 1)
            .first()
        )

        assert empleado is not None
        assert empleado.calendario_token is not None
        assert empleado.calendario_token_revoked_at is None
        assert empleado.calendario_enviado_at is not None

        token = _extraer_token(data["calendario_link"])

        assert token == empleado.calendario_token

    def test_token_reutilizado_no_se_regenera(
        self,
        client,
        db,
    ):
        """
        Dos generaciones consecutivas deben reutilizar el mismo token.
        """

        _crear_datos_calendario(db)

        headers = _headers_duenio(client)

        response1 = _generar_calendario(
            client,
            headers,
        )

        assert response1.status_code == 201

        token1 = (
            db.query(Empleado)
            .filter(Empleado.id_empleado == 1)
            .first()
            .calendario_token
        )

        link1 = response1.json()["calendario_link"]

        response2 = _generar_calendario(
            client,
            headers,
        )

        assert response2.status_code == 201

        empleado = (
            db.query(Empleado)
            .filter(Empleado.id_empleado == 1)
            .first()
        )

        token2 = empleado.calendario_token
        link2 = response2.json()["calendario_link"]

        assert token1 == token2
        assert link1 == link2

    # ------------------------------------------------------------------------
    # 2. Revocación
    # ------------------------------------------------------------------------

    def test_revocar_invalida_link(
        self,
        client,
        db,
    ):
        """
        Generar → revocar → feed viejo devuelve 404.

        Luego generar nuevamente debe crear un token nuevo.
        """

        _crear_datos_calendario(db)

        headers = _headers_duenio(client)

        generar = _generar_calendario(
            client,
            headers,
        )

        assert generar.status_code == 201

        link_viejo = generar.json()["calendario_link"]
        token_viejo = _extraer_token(link_viejo)

        # El feed funciona antes de revocar
        feed_before = client.get(
            f"/api/empleados/{token_viejo}/calendario.ics"
        )

        assert feed_before.status_code == 200

        # Revocar
        revocar = client.post(
            "/api/negocios/1/empleados/1/revocar-calendario",
            headers=headers,
        )

        assert revocar.status_code == 200

        data_revocar = revocar.json()

        assert data_revocar["id_empleado"] == 1
        assert data_revocar["calendario_link"] is None

        empleado = (
            db.query(Empleado)
            .filter(Empleado.id_empleado == 1)
            .first()
        )

        assert empleado.calendario_token == token_viejo
        assert empleado.calendario_token_revoked_at is not None

        # El link viejo ya no funciona
        feed_after = client.get(
            f"/api/empleados/{token_viejo}/calendario.ics"
        )

        assert feed_after.status_code == 404

        # Nueva generación
        generar_nuevo = _generar_calendario(
            client,
            headers,
        )

        assert generar_nuevo.status_code == 201

        link_nuevo = generar_nuevo.json()["calendario_link"]
        token_nuevo = _extraer_token(link_nuevo)

        assert token_nuevo != token_viejo

        empleado = (
            db.query(Empleado)
            .filter(Empleado.id_empleado == 1)
            .first()
        )

        assert empleado.calendario_token == token_nuevo
        assert empleado.calendario_token_revoked_at is None

    # ------------------------------------------------------------------------
    # 3. Feed ICS
    # ------------------------------------------------------------------------

    def test_feed_devuelve_ics_con_turnos_futuros(
        self,
        client,
        db,
    ):
        """
        El feed devuelve:
        - 200
        - text/calendar
        - VCALENDAR
        - VEVENT
        - X-WR-CALNAME
        - UID esperado
        """

        datos = _crear_datos_calendario(db)

        turno = _crear_turno(
            db,
            id_empleado=datos["empleado"].id_empleado,
            id_cliente=datos["cliente"].id_cliente,
            id_servicio=datos["servicio"].id_servicio,
            id_negocio=datos["negocio"].id_negocio,
            fecha_inicio_utc=datetime.now(timezone.utc)
            + timedelta(days=1),
        )

        headers = _headers_duenio(client)

        generar = _generar_calendario(
            client,
            headers,
        )

        assert generar.status_code == 201

        link = generar.json()["calendario_link"]
        token = _extraer_token(link)

        response = client.get(
            f"/api/empleados/{token}/calendario.ics"
        )

        assert response.status_code == 200
        assert "text/calendar" in response.headers["content-type"]

        calendar = Calendar.from_ical(response.content)

        assert str(calendar.get("VERSION")) == "2.0"

        assert str(calendar.get("X-WR-CALNAME")) == "TurnoGo - Juan Perez"

        eventos = list(calendar.walk("VEVENT"))
        assert len(eventos) == 1

        event = eventos[0]

        assert str(event["UID"]) == (
            f"turno-{turno.id_turno}@turnogo.com"
        )

        assert str(event.get("SUMMARY")) == "Corte"
        assert str(event.get("LOCATION")) == "Test 123"

    def test_feed_excluye_turnos_pasados(
        self,
        client,
        db,
    ):
        """
        Un turno pasado no debe aparecer en el feed.
        """

        datos = _crear_datos_calendario(db)

        turno_pasado = _crear_turno(
            db,
            id_empleado=datos["empleado"].id_empleado,
            id_cliente=datos["cliente"].id_cliente,
            id_servicio=datos["servicio"].id_servicio,
            id_negocio=datos["negocio"].id_negocio,
            fecha_inicio_utc=datetime.now(timezone.utc)
            - timedelta(days=1),
        )

        turno_futuro = _crear_turno(
            db,
            id_empleado=datos["empleado"].id_empleado,
            id_cliente=datos["cliente"].id_cliente,
            id_servicio=datos["servicio"].id_servicio,
            id_negocio=datos["negocio"].id_negocio,
            fecha_inicio_utc=datetime.now(timezone.utc)
            + timedelta(days=1),
        )

        headers = _headers_duenio(client)

        generar = _generar_calendario(
            client,
            headers,
        )

        token = _extraer_token(
            generar.json()["calendario_link"]
        )

        response = client.get(
            f"/api/empleados/{token}/calendario.ics"
        )

        assert response.status_code == 200

      

        calendar = Calendar.from_ical(response.content)

        eventos = list(calendar.walk("VEVENT"))

        uids = {
            str(event.get("UID"))
            for event in eventos
        }

        assert f"turno-{turno_pasado.id_turno}@turnogo.com" not in uids

        assert f"turno-{turno_futuro.id_turno}@turnogo.com" in uids

    def test_feed_zona_horaria(
        self,
        client,
        db,
    ):
        """
        10:00 UTC debe representar 07:00 en Argentina.
        """

        datos = _crear_datos_calendario(db)

        fecha_utc = _fecha_manana_a_las_10_utc()

        turno = _crear_turno(
            db,
            id_empleado=datos["empleado"].id_empleado,
            id_cliente=datos["cliente"].id_cliente,
            id_servicio=datos["servicio"].id_servicio,
            id_negocio=datos["negocio"].id_negocio,
            fecha_inicio_utc=fecha_utc,
        )

        headers = _headers_duenio(client)

        generar = _generar_calendario(
            client,
            headers,
        )

        token = _extraer_token(
            generar.json()["calendario_link"]
        )

        response = client.get(
            f"/api/empleados/{token}/calendario.ics"
        )

        assert response.status_code == 200

        calendar = Calendar.from_ical(response.content)

        eventos = list(calendar.walk("VEVENT"))

        assert len(eventos) == 1

        event = eventos[0]

        dtstart = event.decoded("DTSTART")

        assert dtstart.hour == 7
        assert dtstart.minute == 0

        # Debe conservar timezone
        assert dtstart.tzinfo is not None

    # ------------------------------------------------------------------------
    # 4. Permisos
    # ------------------------------------------------------------------------

    def test_generar_solo_duenio(
        self,
        client,
        db,
    ):
        """
        Un usuario que no es dueño del negocio no puede
        generar el calendario.
        """

        datos = _crear_datos_calendario(db)

        # Segundo usuario
        usuario_2 = _crear_usuario_duenio(
            db,
            id_us=2,
            email="otro@test.com",
        )

        headers = obtener_token(
            client,
            "otro@test.com",
            "Test1234567!",
        )

        response = client.post(
            "/api/negocios/1/empleados/1/generar-calendario",
            headers=headers,
            json={"email": "juan.perez@test.com"},
        )

        assert response.status_code == 403

    def test_token_invalido_404(
        self,
        client,
        db,
    ):
        """
        Un token aleatorio no debe permitir acceder al feed.
        """

        _crear_datos_calendario(db)

        token_invalido = (
            "token-invalido-"
            "123456789abcdef"
        )

        response = client.get(
            f"/api/empleados/{token_invalido}/calendario.ics"
        )

        assert response.status_code == 404

    # ------------------------------------------------------------------------
    # 5. Duración fallback
    # ------------------------------------------------------------------------

    def test_dtend_con_fallback_duracion_min(
        self,
        client,
        db,
    ):
        """
        Si fecha_hora_fin es NULL:
        DTEND = DTSTART + servicio.duracion_min.
        """

        datos = _crear_datos_calendario(db)

        fecha_inicio = _fecha_manana_a_las_10_utc()

        turno = _crear_turno(
            db,
            id_empleado=datos["empleado"].id_empleado,
            id_cliente=datos["cliente"].id_cliente,
            id_servicio=datos["servicio"].id_servicio,
            id_negocio=datos["negocio"].id_negocio,
            fecha_inicio_utc=fecha_inicio,
            fecha_fin_utc=None,
        )

        headers = _headers_duenio(client)

        generar = _generar_calendario(
            client,
            headers,
        )

        assert generar.status_code == 201

        token = _extraer_token(
            generar.json()["calendario_link"]
        )

        response = client.get(
            f"/api/empleados/{token}/calendario.ics"
        )

        assert response.status_code == 200

        calendar = Calendar.from_ical(response.content)

        eventos = list(calendar.walk("VEVENT"))

        assert len(eventos) == 1

        event = eventos[0]

        dtstart = event.decoded("DTSTART")
        dtend = event.decoded("DTEND")

        assert dtend - dtstart == timedelta(minutes=30)


class TestEmpleadoCalendarioEstado:
    """
    GET /api/negocios/{nid}/empleados/{eid}/calendario-estado
    """

    def _consultar(self, client, headers=None, id_negocio=1, id_empleado=1):
        return client.get(
            f"/api/negocios/{id_negocio}/empleados/{id_empleado}/calendario-estado",
            headers=headers or {},
        )

    def test_sin_calendario_cuando_nunca_se_genero(
        self,
        client,
        db,
    ):
        _crear_datos_calendario(db)

        headers = _headers_duenio(client)

        response = self._consultar(client, headers)

        assert response.status_code == 200

        data = response.json()

        assert data["id_empleado"] == 1
        assert data["estado"] == "sin_calendario"
        assert data["calendario_enviado_at"] is None

    def test_activo_tras_generar(
        self,
        client,
        db,
    ):
        _crear_datos_calendario(db)

        headers = _headers_duenio(client)

        generar = _generar_calendario(client, headers)

        assert generar.status_code == 201

        response = self._consultar(client, headers)

        assert response.status_code == 200

        data = response.json()

        assert data["estado"] == "activo"
        assert data["calendario_enviado_at"] is not None

    def test_revocado_tras_revocar(
        self,
        client,
        db,
    ):
        _crear_datos_calendario(db)

        headers = _headers_duenio(client)

        assert _generar_calendario(client, headers).status_code == 201

        revocar = client.post(
            "/api/negocios/1/empleados/1/revocar-calendario",
            headers=headers,
        )

        assert revocar.status_code == 200

        response = self._consultar(client, headers)

        assert response.status_code == 200

        data = response.json()

        assert data["estado"] == "revocado"

    def test_generar_nuevo_token_vuelve_a_activo(
        self,
        client,
        db,
    ):
        _crear_datos_calendario(db)

        headers = _headers_duenio(client)

        assert _generar_calendario(client, headers).status_code == 201
        assert client.post(
            "/api/negocios/1/empleados/1/revocar-calendario",
            headers=headers,
        ).status_code == 200
        assert _generar_calendario(client, headers).status_code == 201

        response = self._consultar(client, headers)

        assert response.json()["estado"] == "activo"

    def test_requiere_autenticacion(
        self,
        client,
        db,
    ):
        _crear_datos_calendario(db)

        response = self._consultar(client)

        assert response.status_code == 401

    def test_no_duenio_403(
        self,
        client,
        db,
    ):
        _crear_datos_calendario(db)

        _crear_usuario_duenio(
            db,
            id_us=2,
            email="otro@test.com",
        )

        headers = obtener_token(
            client,
            "otro@test.com",
            "Test1234567!",
        )

        response = self._consultar(client, headers)

        assert response.status_code == 403

    def test_empleado_de_otro_negocio_404(
        self,
        client,
        db,
    ):
        datos = _crear_datos_calendario(db)

        usuario_2 = _crear_usuario_duenio(
            db,
            id_us=2,
            email="otro@test.com",
        )

        categoria = Categoria(nombre="Cat Negocio 2")
        db.add(categoria)
        db.flush()

        negocio_2 = Negocio(
            id_negocio=2,
            usuario_id=usuario_2.id_us,
            nombre="Negocio Dos",
            id_categoria=categoria.id_categoria,
            wsp="Test123456789",
            direccion="Test 456",
            ciudad="San Nicolas",
            activo=True,
            slug="negocio-dos",
        )
        db.add(negocio_2)
        db.commit()

        headers = obtener_token(
            client,
            "otro@test.com",
            "Test1234567!",
        )

        response = self._consultar(
            client,
            headers,
            id_negocio=2,
            id_empleado=datos["empleado"].id_empleado,
        )

        assert response.status_code == 404