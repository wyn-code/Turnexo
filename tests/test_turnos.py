
from fastapi.testclient import TestClient


# 1. DUEÑO PUEDE EDITAR SU NEGOCIO (Este estaba bien)
def test_owner_puede_editar_su_negocio(client, seed_data):
    from tests.auth_helpers import obtener_token

    # Usamos test1 porque ES el dueño (usuario_id=1)
    headers = obtener_token(
        client,
        "test1@test.com",
        "Test1234567!"
    )

    payload = {
        "nombre": "Negocio Editado"
    }

    response = client.put(
        f"/api/negocios/{seed_data['negocio'].id_negocio}",
        json=payload,
        headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nombre"] == "Negocio Editado"


# 2. DUEÑO NO PUEDE EDITAR NEGOCIO AJENO
def test_owner_no_puede_editar_negocio_ajeno(client, seed_data):
    from tests.auth_helpers import obtener_token

    # Usamos test2 porque NO es el dueño
    headers = obtener_token(
        client,
        "test2@test.com", 
        "Test1234567!"
    )
    payload = {
        "nombre": "Negocio Hackeado" 
    }
    response = client.put(
        f"/api/negocios/{seed_data['negocio'].id_negocio}",
        json=payload,
        headers=headers
    )
    assert response.status_code == 403


# 3. NO PUEDE BORRAR NEGOCIO AJENO
def test_owner_no_puede_borrar_negocio_ajeno(client, seed_data):
    from tests.auth_helpers import obtener_token

    # Usamos test2
    headers = obtener_token(
        client,
        "test2@test.com",
        "Test1234567!"
    )
    response = client.delete(
        f"/api/negocios/{seed_data['negocio'].id_negocio}",
        headers=headers
    )
    assert response.status_code == 403


# 4. NO PUEDE CREAR SERVICIO EN NEGOCIO AJENO
def test_owner_no_puede_crear_servicio_en_negocio_ajeno(client, seed_data):
    from tests.auth_helpers import obtener_token

    # Usamos test2
    headers = obtener_token(
        client,
        "test2@test.com",
        "Test1234567!"
    )
    payload = {
        "nombre_servicio": "Servicio Test",
        "duracion_min": 60,
        "duracion_max": 60,
        "precio": 1000,
        "requiere_aprobacion": False,
        "id_negocio": seed_data["negocio"].id_negocio,
        "activo": True
    }
    response = client.post(
        "/api/servicios/",
        json=payload,
        headers=headers
    )
    assert response.status_code == 403

