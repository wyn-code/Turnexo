from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from tests.auth_helpers import obtener_token

from app.core.estados_turno import ASISTIO, CONFIRMADO, COMPLETADO, CANCELADO, NO_ASISTIO


def _headers_duenio(client):
    return obtener_token(client, "test1@test.com", "Test1234567!")


def _crear_turno(client, seed_data, telefono="3364555000", fecha=None):
    # Fecha futura por defecto para que los tokens QR no estén vencidos.
    fecha = fecha or (datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )

    res_cliente = client.post(
        "/api/clientes/get-or-create",
        json={"telefono": telefono, "nombre": "Cliente", "apellido": "Test"},
    )
    assert res_cliente.status_code == 200, res_cliente.text
    cliente = res_cliente.json()

    payload = {
        "id_negocio": seed_data["negocio"].id_negocio,
        "id_cliente": cliente["id_cliente"],
        "id_servicio": seed_data["servicio"].id_servicio,
        "id_empleado": seed_data["empleado"].id_empleado,
        "fecha_hora_inicio": fecha.isoformat(),
    }

    res = client.post("/api/turnos/", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def test_turno_nace_confirmado(client: TestClient, seed_data):
    turno = _crear_turno(client, seed_data)
    assert turno["id_estado"] == CONFIRMADO
    # El POST siempre debe devolver qr_token
    assert turno["qr_token"]


def _cambiar_estado(client, seed_data, turno_id, id_estado, motivo=None):
    payload = {"id_estado": id_estado}
    if motivo is not None:
        payload["rechazado_motivo"] = motivo

    return client.put(
        f"/api/turnos/{turno_id}/estado",
        json=payload,
        headers=_headers_duenio(client),
    )


def test_confirmado_a_asistio(client: TestClient, seed_data):
    turno = _crear_turno(client, seed_data)
    res = _cambiar_estado(client, seed_data, turno["id_turno"], ASISTIO)
    assert res.status_code == 200, res.text
    assert res.json()["id_estado"] == ASISTIO


def test_confirmado_a_cancelado(client: TestClient, seed_data):
    turno = _crear_turno(client, seed_data)
    res = _cambiar_estado(
        client, seed_data, turno["id_turno"], CANCELADO, motivo="Cliente pidió cancelar"
    )
    assert res.status_code == 200, res.text
    assert res.json()["id_estado"] == CANCELADO


def test_confirmado_a_no_asistio(client: TestClient, seed_data):
    turno = _crear_turno(client, seed_data)
    res = _cambiar_estado(client, seed_data, turno["id_turno"], NO_ASISTIO)
    assert res.status_code == 200, res.text
    assert res.json()["id_estado"] == NO_ASISTIO


def test_confirmado_a_completado_rechazado(client: TestClient, seed_data):
    # COMPLETADO ya no es una transición permitida desde CONFIRMADO.
    turno = _crear_turno(client, seed_data)
    res = _cambiar_estado(client, seed_data, turno["id_turno"], COMPLETADO)
    assert res.status_code == 400, res.text
    assert "No se puede" in res.json()["detail"]


def test_checkin_qr_marca_asistio(client: TestClient, seed_data):
    from app.services.qr_service import generar_token_qr

    turno = _crear_turno(client, seed_data)

    negocio_id = seed_data["negocio"].id_negocio
    fecha_fin = datetime.fromisoformat(turno["fecha_hora_fin"])

    token = generar_token_qr(turno["id_turno"], negocio_id, fecha_fin)
    res = client.post(
        "/api/turnos/qr/check-in",
        params={"token": token},
        headers=_headers_duenio(client),
    )
    assert res.status_code == 200, res.text
    assert res.json()["id_estado"] == ASISTIO


def test_checkin_qr_doble_rechazado(client: TestClient, seed_data):
    from app.services.qr_service import generar_token_qr

    turno = _crear_turno(client, seed_data)

    negocio_id = seed_data["negocio"].id_negocio
    fecha_fin = datetime.fromisoformat(turno["fecha_hora_fin"])

    token = generar_token_qr(turno["id_turno"], negocio_id, fecha_fin)
    headers = _headers_duenio(client)

    res_1 = client.post(
        "/api/turnos/qr/check-in", params={"token": token}, headers=headers
    )
    assert res_1.status_code == 200, res_1.text

    res_2 = client.post(
        "/api/turnos/qr/check-in", params={"token": token}, headers=headers
    )
    assert res_2.status_code == 400, res_2.text
    assert "ya fue registrado" in res_2.json()["detail"]
