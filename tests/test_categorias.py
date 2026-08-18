from datetime import datetime, timezone

from app.core.security import get_password_hash
from app.models.usuario import Usuario
from tests.auth_helpers import obtener_token


def _admin_headers(client, db):
    usuario = db.query(Usuario).filter(Usuario.usuario_us == "admin").first()
    if not usuario:
        usuario = Usuario(
            usuario_us="admin",
            email_us="admin@test.com",
            contrasena_us=get_password_hash("Admin1234567!"),
            email_verified=True,
            last_2fa_verified_at=datetime.now(timezone.utc).replace(tzinfo=None),
            role="admin",
        )
        db.add(usuario)
        db.commit()
    return obtener_token(client, "admin@test.com", "Admin1234567!")


def test_crear_categoria_con_icono_url_y_descripcion(client, db):
    data = {
        "nombre": "Barberia",
        "icono": "https://example.com/barberia.jpg",
        "descripcion": "Cortes masculinos y barba",
    }

    response = client.post("/api/categorias/", json=data, headers=_admin_headers(client, db))

    assert response.status_code == 200
    body = response.json()
    assert body["id_categoria"]
    assert body["nombre"] == data["nombre"]
    assert body["icono"] == data["icono"]
    assert body["descripcion"] == data["descripcion"]


def test_listar_categorias_ordenadas_por_nombre(client, db):
    headers = _admin_headers(client, db)
    client.post(
        "/api/categorias/",
        json={
            "nombre": "Unas",
            "icono": "https://example.com/unas.png",
            "descripcion": "Manicuria",
        },
        headers=headers,
    )
    client.post(
        "/api/categorias/",
        json={
            "nombre": "Barberia",
            "icono": "https://example.com/barberia.jpg",
            "descripcion": "Barba",
        },
        headers=headers,
    )

    response = client.get("/api/categorias/")

    assert response.status_code == 200
    nombres = [categoria["nombre"] for categoria in response.json()]
    assert nombres == sorted(nombres)


def test_actualizar_categoria_permite_limpiar_icono_y_descripcion(client, db):
    headers = _admin_headers(client, db)
    created = client.post(
        "/api/categorias/",
        json={
            "nombre": "Masajes",
            "icono": "https://example.com/masajes.webp",
            "descripcion": "Masajes relajantes",
        },
        headers=headers,
    ).json()

    response = client.put(
        f"/api/categorias/{created['id_categoria']}",
        json={"icono": None, "descripcion": ""},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["icono"] is None
    assert body["descripcion"] is None


def test_rechaza_url_no_http(client, db):
    response = client.post(
        "/api/categorias/",
        json={
            "nombre": "Estetica",
            "icono": "ftp://example.com/estetica.jpg",
            "descripcion": "Tratamientos de belleza",
        },
        headers=_admin_headers(client, db),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "icono debe ser una URL http(s) valida"