from datetime import datetime, timedelta, UTC, date
from fastapi.testclient import TestClient


def _auth(client):
    from tests.auth_helpers import obtener_token
    return obtener_token(client, "test1@test.com", "Test1234567!")


def _seed_turnos(db, seed_data):
    from app.models.turnos import Turno
    from app.models.cliente import Cliente

    cliente = Cliente(
        id_cliente=1,
        nombre="Carlos",
        apellido="Lopez",
        telefono="111111111",
        email="carlos@test.com",
    )
    db.add(cliente)
    db.flush()

    today = datetime.now(UTC).date()
    turnos_data = [
        (1, COMPLETADO, today, 1000),
        (1, COMPLETADO, today, 1000),
        (1, CANCELADO, today, 1000),
        (1, COMPLETADO, today - timedelta(days=1), 1000),
        (1, CONFIRMADO, today, 1000),
        (1, PENDIENTE, today + timedelta(days=2), 1000),
        (1, COMPLETADO, today - timedelta(days=14), 1000),
    ]

    for cliente_id, estado, dia, precio in turnos_data:
        turno = Turno(
            id_negocio=seed_data["negocio"].id_negocio,
            id_cliente=cliente_id,
            id_servicio=seed_data["servicio"].id_servicio,
            id_empleado=seed_data["empleado"].id_empleado,
            id_estado=estado,
            fecha_hora_inicio=datetime(dia.year, dia.month, dia.day, 10, 0),
        )
        db.add(turno)

    db.commit()


COMPLETADO = 3
CANCELADO = 4
CONFIRMADO = 2
PENDIENTE = 1
NO_ASISTIO = 5
ASISTIO = 6


def test_statistics_returns_all_sections(client, seed_data, db):
    _seed_turnos(db, seed_data)
    headers = _auth(client)

    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()

    assert "kpis" in body
    assert "resumen" in body
    assert "clientes" in body
    assert "servicios" in body
    assert "ingresos" in body
    assert "agenda" in body
    assert "asistencia" in body
    assert "empleados" in body


def test_kpis_have_required_fields(client, seed_data, db):
    _seed_turnos(db, seed_data)
    headers = _auth(client)

    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
        headers=headers,
    )
    body = response.json()
    kpis = body["kpis"]

    assert "ingresoTotal" in kpis
    assert "clientesActivos" in kpis
    assert "servicioMasVendido" in kpis
    assert "diaMasFacturado" in kpis
    assert "horaMayorDemanda" in kpis
    assert "ocupacionAgenda" in kpis

    assert isinstance(kpis["ingresoTotal"]["value"], (int, float))
    assert kpis["ingresoTotal"]["value"] >= 0
    assert isinstance(kpis["servicioMasVendido"], str)
    assert len(kpis["diaMasFacturado"]) > 0
    assert len(kpis["horaMayorDemanda"]) > 0


def test_resumen_turnos_hoy(client, seed_data, db):
    _seed_turnos(db, seed_data)
    headers = _auth(client)

    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
        headers=headers,
    )
    body = response.json()
    resumen = body["resumen"]

    assert resumen["turnosHoy"]["value"] >= 0
    assert isinstance(resumen["turnosPorDia"], list)
    assert len(resumen["turnosPorDia"]) == 7

    for item in resumen["turnosPorDia"]:
        assert "dia" in item
        assert "actual" in item
        assert "anterior" in item


def test_asistencia_counts(client, seed_data, db):
    _seed_turnos(db, seed_data)
    headers = _auth(client)

    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
        headers=headers,
    )
    body = response.json()
    asistencia = body["asistencia"]

    assert asistencia["completados"] >= 0
    assert asistencia["cancelados"] >= 0
    assert asistencia["noShow"] >= 0
    assert asistencia["totalTurnos"] >= 0
    assert isinstance(asistencia["distribucion"], list)
    assert len(asistencia["distribucion"]) > 0


def test_servicios_items(client, seed_data, db):
    _seed_turnos(db, seed_data)
    headers = _auth(client)

    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
        headers=headers,
    )
    body = response.json()
    servicios = body["servicios"]

    assert isinstance(servicios["items"], list)
    for item in servicios["items"]:
        assert "nombre" in item
        assert "solicitados" in item
        assert "ingresos" in item
        assert "tiempo" in item


def test_empleados_list(client, seed_data, db):
    _seed_turnos(db, seed_data)
    headers = _auth(client)

    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
        headers=headers,
    )
    body = response.json()

    assert isinstance(body["empleados"], list)
    for emp in body["empleados"]:
        assert "nombre" in emp
        assert "turnos" in emp
        assert "ingresos" in emp
        assert "ocupacion" in emp


def test_date_range_filter(client, seed_data, db):
    _seed_turnos(db, seed_data)
    headers = _auth(client)

    today = date.today()
    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}"
        f"?date_start={today.isoformat()}&date_end={today.isoformat()}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["asistencia"]["totalTurnos"] >= 0


def test_unauthorized_access_returns_403(client, seed_data):
    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
    )
    assert response.status_code in [401, 403]


def test_other_user_cannot_access(client, seed_data, db):
    _seed_turnos(db, seed_data)
    from tests.auth_helpers import obtener_token
    headers = obtener_token(client, "test2@test.com", "Test1234567!")

    response = client.get(
        f"/api/statistics/business/{seed_data['negocio'].id_negocio}",
        headers=headers,
    )
    assert response.status_code in [403, 404]
