from datetime import datetime, time, timedelta
from fastapi.testclient import TestClient

from tests.auth_helpers import obtener_token


def _headers_duenio(client):
    return obtener_token(client, "test1@test.com", "Test1234567!")


def crear_cliente(client: TestClient, telefono: str, nombre="Rocco", apellido="Lavecchia"):
    res = client.post(
        "/api/clientes/get-or-create",
        json={
            "telefono": telefono,
            "nombre": nombre,
            "apellido": apellido,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_get_or_create_reutiliza_cliente(client: TestClient):
    cliente_1 = crear_cliente(client, "3364123456")
    cliente_2 = crear_cliente(client, "3364123456")

    assert cliente_1["id_cliente"] == cliente_2["id_cliente"]
    assert cliente_1["telefono"] == "3364123456"


def test_crear_turno_y_rechazar_superposicion(client: TestClient, seed_data):
    cliente = crear_cliente(client, "3364999000")

    inicio = datetime(2026, 4, 20, 10, 0, 0)

    payload_1 = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "id_empleado": seed_data["empleado"].id_empleado,
        "fecha_hora_inicio": inicio.isoformat(),
    }

    res_1 = client.post("/api/turnos/", json=payload_1)
    assert res_1.status_code == 201, res_1.text
    turno_1 = res_1.json()

    assert turno_1["id_negocio"] == seed_data["negocio"].id_negocio
    assert turno_1["cliente"]["id_cliente"] == cliente["id_cliente"]
    assert turno_1["servicio"]["id_servicio"] == seed_data["servicio"].id_servicio
    assert turno_1["empleado"]["id_empleado"] == seed_data["empleado"].id_empleado
    assert turno_1["fecha_hora_fin"] is not None

    payload_superpuesto = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "id_empleado": seed_data["empleado"].id_empleado,
        "fecha_hora_inicio": (inicio + timedelta(minutes=15)).isoformat(),
    }

    res_2 = client.post("/api/turnos/", json=payload_superpuesto)
    assert res_2.status_code == 409, res_2.text
    assert "horario" in res_2.json()["detail"].lower()


def test_permite_turno_no_superpuesto(client: TestClient, seed_data):
    cliente = crear_cliente(client, "3364888000")

    inicio_1 = datetime(2026, 4, 21, 10, 0, 0)
    inicio_2 = datetime(2026, 4, 21, 10, 30, 0)

    payload_1 = {
    "id_negocio": seed_data["negocio"].id_negocio,
    "id_cliente": cliente["id_cliente"],
    "id_servicio": seed_data["servicio"].id_servicio,
    "id_empleado": seed_data["empleado"].id_empleado,
    "fecha_hora_inicio": inicio_1.isoformat(),
    }

    res_1 = client.post("/api/turnos/", json=payload_1)
    assert res_1.status_code == 201, res_1.text

    payload_2 = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "id_empleado": seed_data["empleado"].id_empleado,
        "fecha_hora_inicio": inicio_2.isoformat(),
    }

    res_2 = client.post("/api/turnos/", json=payload_2)
    assert res_2.status_code == 201, res_2.text


def test_listar_turnos_por_rango(client: TestClient, seed_data):
    res = client.get(
        "/api/turnos/por-rango",
        params={
            "desde": "2026-04-01T00:00:00",
            "hasta": "2026-05-01T00:00:00",
            "id_empleado": 1,
        },
        headers=_headers_duenio(client),
    )

    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)


def test_disponibilidad_publico_sin_auth(client: TestClient, seed_data):
    res = client.get(
        "/api/turnos/disponibilidad",
        params={
            "id_negocio": seed_data["negocio"].id_negocio,
            "desde": "2026-04-01T00:00:00",
            "hasta": "2026-05-01T00:00:00",
        },
    )

    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    for turno in data:
        assert "cliente" not in turno
        assert "id_cliente" not in turno


def test_disponibilidad_rechaza_rango_invalido(client: TestClient, seed_data):
    res = client.get(
        "/api/turnos/disponibilidad",
        params={
            "id_negocio": seed_data["negocio"].id_negocio,
            "desde": "2026-05-01T00:00:00",
            "hasta": "2026-04-01T00:00:00",
        },
    )

    assert res.status_code == 400


def test_rechaza_turno_con_empleado_de_otro_negocio(client: TestClient, db, seed_data):
    from app.models.empleado import Empleado
    from app.models.negocio import Negocio

    otro_negocio = Negocio(
        id_negocio=2,
        usuario_id=2,
        nombre="Otro Negocio",
        id_categoria=1,
        wsp="3364000002",
        direccion="Otra 123",
        ciudad="San Nicolas",
        activo=True,
        slug="otro-negocio",
    )
    empleado_ajeno = Empleado(
        id_empleado=2,
        id_negocio=2,
        nombre="Ana",
        apellido="Gomez",
        telefono="3364777000",
        activo=True,
    )
    db.add_all([otro_negocio, empleado_ajeno])
    db.commit()

    cliente = crear_cliente(client, "3364777001")
    payload = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "id_empleado": empleado_ajeno.id_empleado,
        "fecha_hora_inicio": datetime(2026, 4, 22, 10, 0, 0).isoformat(),
    }

    res = client.post("/api/turnos/", json=payload)
    assert res.status_code == 400, res.text
    assert "empleado" in res.json()["detail"].lower()


def test_rechaza_superposicion_sin_empleado(client: TestClient, seed_data):
    cliente = crear_cliente(client, "3364777002")
    inicio = datetime(2026, 4, 23, 10, 0, 0)

    payload_1 = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "fecha_hora_inicio": inicio.isoformat(),
    }
    res_1 = client.post("/api/turnos/", json=payload_1)
    assert res_1.status_code == 201, res_1.text

    payload_2 = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "fecha_hora_inicio": (inicio + timedelta(minutes=15)).isoformat(),
    }
    res_2 = client.post("/api/turnos/", json=payload_2)
    assert res_2.status_code == 409, res_2.text


def test_rechaza_turno_fuera_del_horario_del_negocio(client: TestClient, db, seed_data):
    from app.models.horarios_negocio import HorarioNegocio

    db.add(HorarioNegocio(
        id_negocio=seed_data["negocio"].id_negocio,
        dia_semana=0,
        hora_apertura=time(10, 0),
        hora_cierre=time(11, 0),
    ))
    db.commit()

    cliente = crear_cliente(client, "3364777003")
    payload = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "id_empleado": seed_data["empleado"].id_empleado,
        "fecha_hora_inicio": datetime(2026, 4, 20, 9, 0, 0).isoformat(),
    }

    res = client.post("/api/turnos/", json=payload)
    assert res.status_code == 400, res.text
    assert "horario" in res.json()["detail"].lower()
