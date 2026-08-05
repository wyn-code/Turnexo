from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException

from app.models.plan import Plan
from app.models.plan_feature import PlanFeature
from app.models.suscripcion import Suscripcion
from app.services import payment_service


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


def test_crear_preferencia_mp_ok(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    mock_result = {
        "status": 201,
        "response": {
            "id": "pref_test_123",
            "init_point": "https://mercadopago.com/checkout/test",
        },
    }

    with patch.object(payment_service.sdk, "preference") as mock_pref:
        mock_pref.return_value.create.return_value = mock_result

        result = payment_service.crear_preferencia_mp(db, negocio, plan)

    assert result["init_point"] == "https://mercadopago.com/checkout/test"
    assert result["preference_id"] == "pref_test_123"

    suscripcion = (
        db.query(Suscripcion)
        .filter(Suscripcion.id_negocio == negocio.id_negocio)
        .first()
    )
    assert suscripcion is not None
    assert suscripcion.estado == "pendiente"
    assert suscripcion.proveedor_pago == "mercadopago"
    assert suscripcion.external_subscription_id == "pref_test_123"


def test_crear_preferencia_mp_error_mercadopago(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    mock_result = {"status": 400, "response": {}}

    with patch.object(payment_service.sdk, "preference") as mock_pref:
        mock_pref.return_value.create.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            payment_service.crear_preferencia_mp(db, negocio, plan)

        assert exc.value.status_code == 502


def test_procesar_pago_exitoso_suscripcion_pendiente_existente(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="pendiente",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
        proveedor_pago="mercadopago",
        external_subscription_id="pref_test_456",
    )
    db.add(suscripcion)
    db.commit()

    result = payment_service.procesar_pago_exitoso(
        db, negocio.id_negocio, plan.id_plan, "pref_test_456"
    )

    assert result.estado == "activa"
    assert result.external_subscription_id == "pref_test_456"


def test_procesar_pago_exitoso_sin_suscripcion_previa(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    result = payment_service.procesar_pago_exitoso(
        db, negocio.id_negocio, plan.id_plan, "pref_test_789"
    )

    assert result.estado == "activa"
    assert result.external_subscription_id == "pref_test_789"


def test_procesar_pago_exitoso_fallback_sin_preference_id(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="pendiente",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
        proveedor_pago="mercadopago",
        external_subscription_id="pref_real_1",
    )
    db.add(suscripcion)
    db.commit()

    result = payment_service.procesar_pago_exitoso(
        db, negocio.id_negocio, plan.id_plan, ""
    )

    assert result.id_suscripcion == suscripcion.id_suscripcion
    assert result.estado == "activa"


def test_procesar_pago_exitoso_cancela_otras_pendientes(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    justa = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="pendiente",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
        proveedor_pago="mercadopago",
        external_subscription_id="pref_vieja_1",
    )
    db.add(justa)
    db.flush()

    db.add(Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="pendiente",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
        proveedor_pago="mercadopago",
        external_subscription_id="pref_vieja_2",
    ))
    db.commit()

    result = payment_service.procesar_pago_exitoso(
        db, negocio.id_negocio, plan.id_plan, "pref_vieja_1"
    )

    pendientes = (
        db.query(Suscripcion)
        .filter(
            Suscripcion.id_negocio == negocio.id_negocio,
            Suscripcion.estado == "pendiente",
        )
        .all()
    )
    assert result.estado == "activa"
    assert len(pendientes) == 0


def test_procesar_pago_exitoso_renueva_suscripcion_activa(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]
    fecha_fin = datetime.now() + timedelta(days=5)

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="activa",
        fecha_inicio=datetime.now(),
        fecha_fin=fecha_fin,
        proveedor_pago="mercadopago",
        external_subscription_id="pref_activa_1",
    )
    db.add(suscripcion)
    db.commit()

    result = payment_service.procesar_pago_exitoso(
        db, negocio.id_negocio, plan.id_plan, "pref_activa_1"
    )

    activas = (
        db.query(Suscripcion)
        .filter(
            Suscripcion.id_negocio == negocio.id_negocio,
            Suscripcion.estado == "activa",
        )
        .all()
    )
    assert result.estado == "activa"
    assert len(activas) == 1
    assert result.fecha_fin == fecha_fin + timedelta(days=plan.duracion_dias)


def test_obtener_suscripcion_actual_con_suscripcion(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="activa",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
    )
    db.add(suscripcion)
    db.commit()

    result = payment_service.obtener_suscripcion_actual(db, negocio.id_negocio)
    assert result is not None
    assert result.estado == "activa"


def test_obtener_suscripcion_actual_sin_suscripcion(db, seed_data):
    negocio = seed_data["negocio"]
    result = payment_service.obtener_suscripcion_actual(db, negocio.id_negocio)
    assert result is None


def test_cancelar_suscripcion_activa(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="activa",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
    )
    db.add(suscripcion)
    db.commit()

    result = payment_service.cancelar_suscripcion(db, suscripcion.id_suscripcion, negocio.id_negocio)
    assert result.estado == "cancelada"


def test_cancelar_suscripcion_ya_cancelada_error(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="cancelada",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
    )
    db.add(suscripcion)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        payment_service.cancelar_suscripcion(db, suscripcion.id_suscripcion, negocio.id_negocio)
    assert exc.value.status_code == 400


def test_cancelar_suscripcion_inexistente_error(db, seed_data):
    negocio = seed_data["negocio"]

    with pytest.raises(HTTPException) as exc:
        payment_service.cancelar_suscripcion(db, 999, negocio.id_negocio)
    assert exc.value.status_code == 404


def test_toggle_renovacion_automatica_apagar(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="activa",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
        renovacion_automatica=True,
    )
    db.add(suscripcion)
    db.commit()

    result = payment_service.toggle_renovacion_automatica(
        db, suscripcion.id_suscripcion, negocio.id_negocio, False
    )
    assert result.renovacion_automatica is False


def test_toggle_renovacion_automatica_encender(db, seed_data):
    plan = _crear_plan_basico(db)
    negocio = seed_data["negocio"]

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="activa",
        fecha_inicio=datetime.now(),
        fecha_fin=datetime.now() + timedelta(days=30),
        renovacion_automatica=False,
    )
    db.add(suscripcion)
    db.commit()

    result = payment_service.toggle_renovacion_automatica(
        db, suscripcion.id_suscripcion, negocio.id_negocio, True
    )
    assert result.renovacion_automatica is True
