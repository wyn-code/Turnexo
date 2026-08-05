from datetime import datetime, timedelta
from tests.auth_helpers import obtener_token
from app.models.plan import Plan
from app.models.plan_feature import PlanFeature
from app.models.suscripcion import Suscripcion


def _headers_duenio(client):
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

    db.add_all([
        PlanFeature(id_plan=plan.id_plan, feature_key="mapa_ubicacion"),
        PlanFeature(id_plan=plan.id_plan, feature_key="imagenes_personalizadas"),
    ])
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
        estado="activa",
        fecha_inicio=datetime.now() - timedelta(days=60),
        fecha_fin=datetime.now() - timedelta(days=1),
    )
    db.add(suscripcion)
    db.commit()
    return suscripcion


# ─── MAPA ────────────────────────────────────────────────────────────────────

def test_mapa_no_devuelve_negocios_free(client, db, seed_data):
    # negocio existe pero no tiene suscripción VIP
    _crear_plan_vip_con_features(db)

    response = client.get("/api/negocios/mapa")
    assert response.status_code == 200
    assert response.json() == []


def test_mapa_devuelve_negocio_vip_con_coordenadas(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)

    # Agregar coordenadas al negocio
    negocio.latitud = -33.3
    negocio.longitud = -60.2
    db.commit()

    response = client.get("/api/negocios/mapa")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id_negocio"] == negocio.id_negocio
    assert data[0]["latitud"] == -33.3
    assert data[0]["longitud"] == -60.2


def test_mapa_no_devuelve_negocio_vip_sin_coordenadas(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)

    # negocio VIP pero sin coordenadas cargadas
    negocio.latitud = None
    negocio.longitud = None
    db.commit()

    response = client.get("/api/negocios/mapa")
    assert response.status_code == 200
    assert response.json() == []


def test_mapa_no_devuelve_negocio_con_suscripcion_vencida(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_vencida(db, negocio.id_negocio, plan.id_plan)

    negocio.latitud = -33.3
    negocio.longitud = -60.2
    db.commit()

    response = client.get("/api/negocios/mapa")
    assert response.status_code == 200
    assert response.json() == []


# ─── IMÁGENES ────────────────────────────────────────────────────────────────

def test_negocio_free_no_puede_subir_imagenes(client, db, seed_data):
    # negocio sin suscripción VIP intenta actualizar imágenes
    _crear_plan_vip_con_features(db)  # plan existe pero el negocio no tiene suscripción

    response = client.put(
        f"/api/negocios/{seed_data['negocio'].id_negocio}",
        json={"imagenes": ["https://cdn.test/foto1.jpg"]},
        headers=_headers_duenio(client),
    )
    assert response.status_code == 403
    assert "VIP" in response.json()["detail"]


def test_negocio_vip_puede_subir_imagenes(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_activa(db, negocio.id_negocio, plan.id_plan)

    response = client.put(
        f"/api/negocios/{negocio.id_negocio}",
        json={"imagenes": ["https://cdn.test/foto1.jpg", "https://cdn.test/foto2.jpg"]},
        headers=_headers_duenio(client),
    )
    assert response.status_code == 200

    imagenes = response.json()["imagenes"]
    assert len(imagenes) == 2
    assert imagenes[0]["es_portada"] is True
    assert imagenes[0]["url"] == "https://cdn.test/foto1.jpg"


def test_negocio_vip_vencido_no_puede_subir_imagenes(client, db, seed_data):
    plan = _crear_plan_vip_con_features(db)
    negocio = seed_data["negocio"]
    _crear_suscripcion_vencida(db, negocio.id_negocio, plan.id_plan)

    response = client.put(
        f"/api/negocios/{negocio.id_negocio}",
        json={"imagenes": ["https://cdn.test/foto1.jpg"]},
        headers=_headers_duenio(client),
    )
    assert response.status_code == 403



def test_negocio_free_puede_actualizar_otros_campos(client, db, seed_data):
    # Free puede cambiar nombre, descripción, etc. — solo imágenes están bloqueadas
    _crear_plan_vip_con_features(db)

    response = client.put(
        f"/api/negocios/{seed_data['negocio'].id_negocio}",
        json={"nombre": "Nuevo Nombre", "descripcion": "Nueva descripción"},
        headers=_headers_duenio(client),
    )
    assert response.status_code == 200
    assert response.json()["nombre"] == "Nuevo Nombre"