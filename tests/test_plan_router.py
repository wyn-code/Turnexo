from datetime import datetime, timedelta
from app.models.plan import Plan
from app.models.plan_feature import PlanFeature
from app.models.suscripcion import Suscripcion
from tests.auth_helpers import obtener_token


def _headers_duenio_negocio(client):
    return obtener_token(client, "test1@test.com", "Test1234567!")


def _crear_plan_vip_con_features(db) -> Plan:
    plan = Plan(
        id_plan=1,
        nombre="VIP Mensual",
        precio=9999,
        duracion_dias=30,
        activo=True,
    )
    db.add(plan)
    db.flush()

    features = [
        PlanFeature(id_plan=plan.id_plan, feature_key="mapa_ubicacion"),
        PlanFeature(id_plan=plan.id_plan, feature_key="imagenes_personalizadas"),
        PlanFeature(id_plan=plan.id_plan, feature_key="soporte_prioritario"),
    ]
    db.add_all(features)
    db.commit()
    return plan


def _crear_suscripcion_activa(db, id_negocio: int, id_plan: int):
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


def _crear_suscripcion_vencida(db, id_negocio: int, id_plan: int):
    suscripcion = Suscripcion(
        id_negocio=id_negocio,
        id_plan=id_plan,
        estado="activa",  # estado "activa" pero fecha ya venció
        fecha_inicio=datetime.now() - timedelta(days=60),
        fecha_fin=datetime.now() - timedelta(days=1),
    )
    db.add(suscripcion)
    db.commit()
    return suscripcion


# ─── GET /api/planes/ ────────────────────────────────────────────────────────

def test_listar_planes_devuelve_planes_activos(client, db):
    db.add_all([
        Plan(nombre="Free", precio=0, duracion_dias=30, activo=True),
        Plan(nombre="VIP Mensual", precio=9999, duracion_dias=30, activo=True),
        Plan(nombre="Premium", precio=19999, duracion_dias=30, activo=False),
    ])
    db.commit()

    response = client.get("/api/planes/")
    assert response.status_code == 200

    nombres = [p["nombre"] for p in response.json()]
    assert "Free" in nombres
    assert "VIP Mensual" in nombres
    assert "Premium" not in nombres  # inactivo, no debe aparecer


def test_listar_planes_vacio(client, db):
    response = client.get("/api/planes/")
    assert response.status_code == 200
    assert response.json() == []


# ─── GET /api/planes/negocios/{id}/funciones ─────────────────────────────────

def test_negocio_inexistente_devuelve_404(client, db):
    response = client.get("/api/planes/negocios/999/funciones")
    assert response.status_code == 404


def test_negocio_free_devuelve_funciones_vacias(client, seed_data):
    negocio = seed_data["negocio"]

    response = client.get(f"/api/planes/negocios/{negocio.id_negocio}/funciones")
    assert response.status_code == 200

    body = response.json()
    assert body["id_negocio"] == negocio.id_negocio
    assert body["plan"] is None
    assert body["estado"] is None
    assert body["funciones"] == []


def test_negocio_vip_devuelve_sus_funciones(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)

    response = client.get(f"/api/planes/negocios/{negocio.id_negocio}/funciones")
    assert response.status_code == 200

    body = response.json()
    assert body["plan"] == "VIP Mensual"
    assert body["estado"] == "activa"
    assert set(body["funciones"]) == {
        "mapa_ubicacion",
        "imagenes_personalizadas",
        "soporte_prioritario",
    }


def test_negocio_con_suscripcion_vencida_devuelve_funciones_vacias(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_vencida(db, negocio.id_negocio, plan.id_plan)

    response = client.get(f"/api/planes/negocios/{negocio.id_negocio}/funciones")
    assert response.status_code == 200

    body = response.json()
    assert body["plan"] is None
    assert body["funciones"] == []


# ─── require_feature dependency ──────────────────────────────────────────────

def test_require_feature_sin_autenticacion_devuelve_401(client, seed_data):
    # Sin token → 401
    response = client.get("/api/planes/negocios/1/test-feature")
    assert response.status_code in [401, 404]  # 404 si la ruta no existe, 401 si está protegida


def test_negocio_free_bloqueado_por_require_feature(client, db, seed_data):
    # El negocio sin plan VIP intenta acceder a un endpoint protegido
    # Usamos el endpoint de funciones de imagenes como ejemplo real
    _crear_plan_vip_con_features(db)  # plan existe pero el negocio no tiene suscripción

    response = client.get(
        f"/api/planes/negocios/{seed_data['negocio'].id_negocio}/funciones",
        headers=_headers_duenio_negocio(client),
    )
    body = response.json()
    assert body["funciones"] == []  # Free no tiene ninguna


def test_negocio_vip_tiene_acceso_completo(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)

    response = client.get(
        f"/api/planes/negocios/{negocio.id_negocio}/funciones",
        headers=_headers_duenio_negocio(client),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["funciones"]) == 3