from datetime import datetime, timezone

from app.models.usuario import Usuario
from app.core.security import get_password_hash

from tests.auth_helpers import obtener_token


def _recent_2fa():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _crear_admin(db):
    admin = Usuario(
        id_us=100,
        usuario_us="adminprincipal",
        email_us="admin@test.com",
        contrasena_us=get_password_hash("Admin123456!"),
        email_verified=True,
        role="admin",
        last_2fa_verified_at=_recent_2fa(),
    )
    db.add(admin)
    db.commit()
    return admin


# ---------------- /usuarios: admin vs duenio ----------------

def test_usuario_no_admin_no_puede_listar_usuarios(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.get("/api/usuarios", headers=headers)
    assert response.status_code == 403


def test_usuario_no_admin_no_puede_listar_usuarios_admin(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.get("/api/usuarios/admin", headers=headers)
    assert response.status_code == 403


def test_usuario_puede_leer_su_perfil(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.get("/api/usuarios/1", headers=headers)
    assert response.status_code == 200


def test_usuario_no_puede_leer_perfil_ajeno(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.get("/api/usuarios/2", headers=headers)
    assert response.status_code == 403


def test_usuario_puede_editar_su_perfil(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.put(
        "/api/usuarios/1",
        json={"usuario_us": "testuser1"},
        headers=headers,
    )
    assert response.status_code == 200


def test_usuario_no_puede_editar_perfil_ajeno(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.put(
        "/api/usuarios/2",
        json={"usuario_us": "otro"},
        headers=headers,
    )
    assert response.status_code == 403


def test_usuario_no_puede_cambiar_estado_de_otro(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.patch(
        "/api/usuarios/2/estado",
        json={"estado": False},
        headers=headers,
    )
    assert response.status_code == 403


def test_usuario_no_puede_borrar_otro(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.delete("/api/usuarios/2", headers=headers)
    assert response.status_code == 403


def test_admin_puede_listar_usuarios_admin(client, db):
    _crear_admin(db)
    headers = obtener_token(client, "admin@test.com", "Admin123456!")

    response = client.get("/api/usuarios/admin", headers=headers)
    assert response.status_code == 200


def test_usuario_no_admin_no_puede_ver_negocios_admin(client, seed_data):
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.get("/api/negocios/admin", headers=headers)
    assert response.status_code == 403


def test_admin_puede_ver_negocios_admin(client, db):
    _crear_admin(db)
    headers = obtener_token(client, "admin@test.com", "Admin123456!")

    response = client.get("/api/negocios/admin", headers=headers)
    assert response.status_code == 200
