from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.plan import Plan
from app.models.plan_feature import PlanFeature
from app.models.suscripcion import Suscripcion
from app.services import payment_service
from tests.auth_helpers import obtener_token


def _headers_duenio(client):
    return obtener_token(client, "test1@test.com", "Test1234567!")


def _crear_plan_basico(db) -> Plan:
    plan = Plan(
        id_plan=1,
        nombre="Básico",
        precio=4999,
        duracion_dias=30,
        activo=True,
    )
    db.add(plan)
    db.flush()
    db.add(PlanFeature(id_plan=plan.id_plan, feature_key="mapa_ubicacion"))
    db.commit()
    return plan


def _crear_suscripcion_activa(db, id_negocio, id_plan) -> Suscripcion:
    suscripcion = Suscripcion(
        id_negocio=id_negocio,
        id_plan=id_plan,
        estado="activa",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
    )
    db.add(suscripcion)
    db.commit()
    return suscripcion


# ─── POST /api/pagos/crear-preferencia ─────────────────────────────────

def test_crear_preferencia_exitoso(client, db, seed_data):
    plan = _crear_plan_basico(db)
    headers = _headers_duenio(client)

    mock_result = {
        "status": 201,
        "response": {
            "id": "pref_test_1",
            "init_point": "https://mercadopago.com/checkout/test_1",
        },
    }

    with patch.object(payment_service.sdk, "preference") as mock_pref:
        mock_pref.return_value.create.return_value = mock_result

        response = client.post(
            "/api/pagos/crear-preferencia",
            json={"id_plan": plan.id_plan},
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["init_point"] == "https://mercadopago.com/checkout/test_1"
    assert body["preference_id"] == "pref_test_1"


def test_crear_preferencia_plan_inexistente(client, db, seed_data):
    headers = _headers_duenio(client)

    response = client.post(
        "/api/pagos/crear-preferencia",
        json={"id_plan": 999},
        headers=headers,
    )

    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"].lower()


def test_crear_preferencia_sin_autenticacion(client, db, seed_data):
    response = client.post(
        "/api/pagos/crear-preferencia",
        json={"id_plan": 1},
    )

    assert response.status_code == 401


# ─── GET /api/pagos/suscripcion/actual ─────────────────────────────────

def test_suscripcion_actual_con_suscripcion(client, db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)
    headers = _headers_duenio(client)

    response = client.get("/api/pagos/suscripcion/actual", headers=headers)
    assert response.status_code == 200

    body = response.json()
    assert body["estado"] == "activa"
    assert body["plan"]["nombre"] == "Básico"


def test_suscripcion_actual_sin_suscripcion(client, db, seed_data):
    headers = _headers_duenio(client)

    response = client.get("/api/pagos/suscripcion/actual", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_suscripcion_actual_sin_autenticacion(client, db, seed_data):
    response = client.get("/api/pagos/suscripcion/actual")
    assert response.status_code == 401


# ─── POST /api/pagos/suscripcion/{id}/cancelar ─────────────────────────

def test_cancelar_suscripcion_exitoso(client, db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]
    suscripcion = _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)
    headers = _headers_duenio(client)

    response = client.post(
        f"/api/pagos/suscripcion/{suscripcion.id_suscripcion}/cancelar",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "cancelada"


def test_cancelar_suscripcion_inexistente(client, db, seed_data):
    headers = _headers_duenio(client)

    response = client.post(
        "/api/pagos/suscripcion/999/cancelar",
        headers=headers,
    )

    assert response.status_code == 404


def test_cancelar_suscripcion_sin_autenticacion(client, db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]
    suscripcion = _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)

    response = client.post(
        f"/api/pagos/suscripcion/{suscripcion.id_suscripcion}/cancelar",
    )

    assert response.status_code == 401


# ─── PUT /api/pagos/suscripcion/{id}/renovacion-automatica ─────────────

def test_toggle_renovacion_automatica(client, db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]
    suscripcion = _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)
    headers = _headers_duenio(client)

    response = client.put(
        f"/api/pagos/suscripcion/{suscripcion.id_suscripcion}/renovacion-automatica",
        json={"renovacion_automatica": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["renovacion_automatica"] is False


def test_toggle_renovacion_automatica_sin_auth(client, db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]
    suscripcion = _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)

    response = client.put(
        f"/api/pagos/suscripcion/{suscripcion.id_suscripcion}/renovacion-automatica",
        json={"renovacion_automatica": False},
    )

    assert response.status_code == 401


# ─── POST /api/pagos/webhook ──────────────────────────────────────────

def test_webhook_pago_aprobado(client, db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    external_ref = f"{negocio.id_negocio}:{plan.id_plan}"

    mock_payment_response = {
        "status": 200,
        "response": {
            "status": "approved",
            "external_reference": external_ref,
            "preference_id": "pref_webhook_1",
        },
    }

    with patch.object(payment_service.sdk, "payment") as mock_payment:
        mock_payment.return_value.get.return_value = mock_payment_response

        response = client.post(
            "/api/pagos/webhook?topic=payment&id=12345",
        )

    assert response.status_code == 200

    suscripcion = (
        db.query(Suscripcion)
        .filter(Suscripcion.id_negocio == negocio.id_negocio)
        .first()
    )
    assert suscripcion is not None
    assert suscripcion.estado == "activa"
