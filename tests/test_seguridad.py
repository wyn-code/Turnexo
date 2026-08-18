from datetime import datetime

from app.models.empleado import Empleado
from app.models.negocio import Negocio
from tests.auth_helpers import obtener_token


def _headers_duenio(client):
    return obtener_token(client, "test1@test.com", "Test1234567!")


def _headers_otro(client):
    return obtener_token(client, "test2@test.com", "Test1234567!")


def _crear_negocio_ajeno(db) -> Negocio:
    negocio_ajeno = Negocio(
        id_negocio=2,
        usuario_id=2,
        nombre="Negocio Ajeno",
        id_categoria=1,
        wsp="Test1234567!789",
        direccion="Otra 456",
        ciudad="San Nicolas",
        activo=True,
        slug="negocio-ajeno",
    )
    db.add(negocio_ajeno)
    db.commit()
    return negocio_ajeno


# ---------------- EMPLEADOS ----------------

def test_empleados_listar_requiere_id_negocio(client, db, seed_data):
    response = client.get("/api/empleados/")
    assert response.status_code == 422


def test_empleados_listar_publico_por_negocio(client, db, seed_data):
    response = client.get("/api/empleados/?id_negocio=1")
    assert response.status_code == 200


def test_empleados_obtener_sin_auth(client, db, seed_data):
    response = client.get("/api/empleados/1")
    assert response.status_code == 401


def test_empleados_obtener_propio(client, db, seed_data):
    response = client.get("/api/empleados/1", headers=_headers_duenio(client))
    assert response.status_code == 200


def test_empleados_obtener_ajeno(client, db, seed_data):
    _crear_negocio_ajeno(db)
    db.add(
        Empleado(
            id_empleado=2,
            id_negocio=2,
            nombre="Ajeno",
            apellido="Uno",
            telefono="123",
            activo=True,
        )
    )
    db.commit()

    response = client.get("/api/empleados/2", headers=_headers_duenio(client))
    assert response.status_code == 403


def test_empleados_crear_sin_auth(client, db, seed_data):
    response = client.post(
        "/api/empleados/",
        json={
            "id_negocio": 1,
            "nombre": "Carlos",
            "apellido": "Gomez",
            "telefono": "123456",
            "activo": True,
        },
    )
    assert response.status_code == 401


def test_empleados_crear_en_negocio_ajeno(client, db, seed_data):
    _crear_negocio_ajeno(db)
    response = client.post(
        "/api/empleados/",
        json={
            "id_negocio": 2,
            "nombre": "Carlos",
            "apellido": "Gomez",
            "telefono": "123456",
            "activo": True,
        },
        headers=_headers_duenio(client),
    )
    assert response.status_code == 403


def test_empleados_crear_en_negocio_propio(client, db, seed_data):
    response = client.post(
        "/api/empleados/",
        json={
            "id_negocio": 1,
            "nombre": "Carlos",
            "apellido": "Gomez",
            "telefono": "123456",
            "activo": True,
        },
        headers=_headers_duenio(client),
    )
    assert response.status_code == 200


# ---------------- CLIENTES ----------------

def test_clientes_listar_sin_auth(client, db, seed_data):
    response = client.get("/api/clientes/")
    assert response.status_code == 401


def test_clientes_obtener_sin_auth(client, db, seed_data):
    response = client.get("/api/clientes/1")
    assert response.status_code == 401


def test_clientes_get_or_create_publico(client, db, seed_data):
    response = client.post(
        "/api/clientes/get-or-create",
        json={
            "telefono": "3364123456",
            "nombre": "Cliente",
            "apellido": "Prueba",
        },
    )
    assert response.status_code == 200


def test_clientes_listar_solo_negocio_propio(client, db, seed_data):
    from app.models.cliente import Cliente
    from app.models.turnos import Turno

    cliente_propio = Cliente(
        telefono="222222",
        nombre="Propio",
        apellido="Turno",
    )
    db.add(cliente_propio)
    db.commit()

    db.add(
        Turno(
            id_negocio=1,
            id_cliente=cliente_propio.id_cliente,
            id_servicio=seed_data["servicio"].id_servicio,
            id_empleado=seed_data["empleado"].id_empleado,
            id_estado=seed_data["estado_pendiente"].id_estado,
            fecha_hora_inicio=datetime.now(),
        )
    )
    db.commit()

    response = client.get("/api/clientes/", headers=_headers_otro(client))
    assert response.status_code == 200
    assert response.json() == []

    response = client.get("/api/clientes/", headers=_headers_duenio(client))
    assert response.status_code == 200
    ids = [c["id_cliente"] for c in response.json()]
    assert cliente_propio.id_cliente in ids


# ---------------- HORARIOS ----------------

def _payload_horarios():
    return [
        {
            "dia_semana": 1,
            "hora_apertura": "09:00:00",
            "hora_cierre": "18:00:00",
        }
    ]


def test_horarios_crear_sin_auth(client, db, seed_data):
    response = client.post("/api/horarios/1", json=_payload_horarios())
    assert response.status_code == 401


def test_horarios_crear_propio(client, db, seed_data):
    response = client.post(
        "/api/horarios/1",
        json=_payload_horarios(),
        headers=_headers_duenio(client),
    )
    assert response.status_code == 200


def test_horarios_crear_ajeno(client, db, seed_data):
    _crear_negocio_ajeno(db)
    response = client.post(
        "/api/horarios/2",
        json=_payload_horarios(),
        headers=_headers_duenio(client),
    )
    assert response.status_code == 403


# ---------------- TURNOS POR RANGO ----------------

def test_turnos_por_rango_sin_auth(client, db, seed_data):
    response = client.get(
        "/api/turnos/por-rango",
        params={
            "desde": "2026-08-01T00:00:00",
            "hasta": "2026-08-31T00:00:00",
        },
    )
    assert response.status_code == 401


def test_turnos_por_rango_propio(client, db, seed_data):
    response = client.get(
        "/api/turnos/por-rango",
        params={
            "desde": "2026-08-01T00:00:00",
            "hasta": "2026-08-31T00:00:00",
        },
        headers=_headers_duenio(client),
    )
    assert response.status_code == 200


# ---------------- CATEGORIAS ----------------

def test_categorias_crear_sin_auth(client, db, seed_data):
    response = client.post("/api/categorias/", json={"nombre": "Nueva"})
    assert response.status_code == 401


def test_categorias_crear_no_admin(client, db, seed_data):
    response = client.post(
        "/api/categorias/",
        json={"nombre": "Nueva"},
        headers=_headers_duenio(client),
    )
    assert response.status_code == 403


# ---------------- PLANES ----------------

def test_plan_funciones_sin_auth(client, db, seed_data):
    response = client.get("/api/planes/negocios/1/funciones")
    assert response.status_code == 401


def test_plan_funciones_propio(client, db, seed_data):
    response = client.get(
        "/api/planes/negocios/1/funciones",
        headers=_headers_duenio(client),
    )
    assert response.status_code == 200


def test_plan_funciones_ajeno(client, db, seed_data):
    _crear_negocio_ajeno(db)
    response = client.get(
        "/api/planes/negocios/2/funciones",
        headers=_headers_duenio(client),
    )
    assert response.status_code == 403


# ---------------- GEOREF ----------------

def test_georef_test_geocoding_eliminado(client, db):
    response = client.get("/api/georef/test-geocoding")
    assert response.status_code == 404