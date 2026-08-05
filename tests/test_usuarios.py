import pytest   
from fastapi.testclient import TestClient

# 1. DUEÑO PUEDE EDITAR SU NEGOCIO
def test_owner_puede_editar_su_negocio(client, seed_data):
    from tests.auth_helpers import obtener_token

    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    payload = {
        "nombre": "Negocio Editado",
        "id_categoria": 1,
        "wsp": "123456789",
        "direccion": "Calle Falsa 123",
        "ciudad": "San Nicolas",
        "usuario_id": 1 
    }

    response = client.put(
        f"/api/negocios/{seed_data['negocio'].id_negocio}",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200


# 2. DUEÑO NO PUEDE EDITAR NEGOCIO AJENO
def test_owner_no_puede_editar_negocio_ajeno(client, seed_data):
    from tests.auth_helpers import obtener_token

    headers = obtener_token(client, "test2@test.com", "Test1234567!") # Usa test2

    payload = {
        "nombre": "Negocio Hackeado",
        "id_categoria": 1,
        "wsp": "987654321",
        "direccion": "Otra direccion",
        "ciudad": "San Nicolas",
        "usuario_id": 2 
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

    headers = obtener_token(client, "test2@test.com", "Test1234567!") # 

    response = client.delete(
        f"/api/negocios/{seed_data['negocio'].id_negocio}",
        headers=headers
    )
    # NOTA: Si esto sigue dando 404, revisa si tu URL de borrar es exactamente /api/negocios/{id}
    assert response.status_code == 403


# 4. NO PUEDE CREAR SERVICIO EN NEGOCIO AJENO
def test_owner_no_puede_crear_servicio_en_negocio_ajeno(client, seed_data):
    from tests.auth_helpers import obtener_token

    headers = obtener_token(client, "test2@test.com", "Test1234567!") # 
    # <-- NOMBRES DE CAMPOS CORREGIDOS SEGÚN TU MODELO DE SERVICIO
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


# # 5. NO PUEDE ACCEDER DASHBOARD PRIVADO AJENO
# def test_owner_no_puede_acceder_dashboard_privado_ajeno(client, seed_data):
#     from tests.auth_helpers import obtener_token

#     headers = obtener_token(client, "test2@test.com", "Test1234567!") # <-- CORREGIDO A TEST2

#     response = client.get(
#         f"/api/negocios/{seed_data['negocio'].id_negocio}/dashboard",
#         headers=headers
#     )
#     # NOTA: Si sigue dando 404, revisa que este endpoint exista en tu router
#     assert response.status_code == 403