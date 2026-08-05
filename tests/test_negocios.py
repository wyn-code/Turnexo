from tests.auth_helpers import obtener_token


def headers_duenio_sin_negocio(client):
    return obtener_token(client, "test2@test.com", "Test1234567!")


def test_listar_negocios_vacio(client):
    response = client.get("/api/negocios/")
    assert response.status_code == 200
    assert response.json() == []


def test_traer_negocio_inexistente_por_id(client):
    response = client.get("/api/negocios/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Negocio no encontrado"}


def test_traer_negocio_inexistente_por_slug(client):
    response = client.get("/api/negocios/slug/no-existe")
    assert response.status_code == 404
    assert response.json() == {"detail": "Negocio no encontrado"}


def test_crear_negocio(client, seed_data):
    data = {
        "nombre": "Barberia Rocco",
        "wsp": "3364000000",
        "telefono": "3364000000",
        "direccion": "Mitre 123",
        "ciudad": "San Nicolas",
        "slug": "barberia-rocco",
        "activo": True,
        "usuario_id": 2,
        "id_categoria": 1,
    }

    response = client.post(
        "/api/negocios/",
        json=data,
        headers=headers_duenio_sin_negocio(client),
    )
    assert response.status_code in [200, 201], response.text

    body = response.json()
    assert body["nombre"] == data["nombre"]
    assert body["wsp"] == data["wsp"]
    assert body["telefono"] == data["telefono"]
    assert body["direccion"] == data["direccion"]
    assert body["ciudad"] == data["ciudad"]
    assert body["activo"] == data["activo"]


def test_listar_negocios_con_un_registro(client, seed_data):
    data = {
        "nombre": "Negocio Test",
        "wsp": "3364111111",
        "telefono": "3364111111",
        "direccion": "Belgrano 456",
        "ciudad": "San Nicolas",
        "slug": "negocio-test",
        "activo": True,
        "usuario_id": 2,
        "id_categoria": 1,
    }

    create_response = client.post(
        "/api/negocios/",
        json=data,
        headers=headers_duenio_sin_negocio(client),
    )
    assert create_response.status_code in [200, 201], create_response.text

    list_response = client.get("/api/negocios/")
    assert list_response.status_code == 200

    negocios = list_response.json()
    assert len(negocios) >= 1
    assert any(n["nombre"] == "Negocio Test" for n in negocios)


def test_traer_negocio_por_id(client, seed_data):
    data = {
        "nombre": "Negocio ID Test",
        "wsp": "3364222222",
        "telefono": "3364222222",
        "direccion": "Test 123",
        "ciudad": "San Nicolas",
        "slug": "negocio-id-test",
        "activo": True,
        "usuario_id": 2,
        "id_categoria": 1,
    }

    create_response = client.post(
        "/api/negocios/",
        json=data,
        headers=headers_duenio_sin_negocio(client),
    )
    assert create_response.status_code in [200, 201], create_response.text

    negocio_creado = create_response.json()
    negocio_id = negocio_creado["id_negocio"]

    get_response = client.get(f"/api/negocios/{negocio_id}")
    assert get_response.status_code == 200

    body = get_response.json()
    assert body["id_negocio"] == negocio_id
    assert body["nombre"] == data["nombre"]


def test_traer_negocio_por_slug(client, seed_data):
    data = {
        "nombre": "Negocio Slug Test",
        "wsp": "3364333333",
        "telefono": "3364333333",
        "direccion": "Slug 123",
        "ciudad": "San Nicolas",
        "slug": "negocio-slug-test",
        "activo": True,
        "usuario_id": 2,
        "id_categoria": 1,
    }

    create_response = client.post(
        "/api/negocios/",
        json=data,
        headers=headers_duenio_sin_negocio(client),
    )
    assert create_response.status_code in [200, 201], create_response.text

    get_response = client.get("/api/negocios/slug/negocio-slug-test")
    assert get_response.status_code == 200

    body = get_response.json()
    print(body)

    assert body["nombre"] == data["nombre"]
    assert body["slug"] == "negocio-slug-test"


def test_crear_negocio_completo_con_imagenes(client, seed_data):
    data = {
        "nombre": "Negocio Imagenes Test",
        "wsp": "3364444444",
        "telefono": "3364444444",
        "direccion": "Imagenes 123",
        "ciudad": "San Nicolas",
        "activo": True,
        "usuario_id": 2,
        "id_categoria": 1,
        "descripcion": "Descripción pública del negocio",
        "logo": "https://cloudinary.com/logo.jpg",
        "imagenes": [
            "https://cloudinary.com/img1.jpg",
            "https://cloudinary.com/img2.jpg",
            "https://cloudinary.com/img3.jpg",
        ],
    }

    response = client.post(
        "/api/negocios/complete",
        json=data,
        headers=headers_duenio_sin_negocio(client),
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["descripcion"] == data["descripcion"]
    assert body["logo"] == data["logo"]
    assert body["imagenes"] == [
        {
            "id_imagen": body["imagenes"][0]["id_imagen"],
            "url": "https://cloudinary.com/img1.jpg",
            "es_portada": True,
            "orden": 0,
        },
        {
            "id_imagen": body["imagenes"][1]["id_imagen"],
            "url": "https://cloudinary.com/img2.jpg",
            "es_portada": False,
            "orden": 1,
        },
        {
            "id_imagen": body["imagenes"][2]["id_imagen"],
            "url": "https://cloudinary.com/img3.jpg",
            "es_portada": False,
            "orden": 2,
        },
    ]


def test_traer_negocio_por_slug_devuelve_imagenes_ordenadas(client, seed_data):
    data = {
        "nombre": "Negocio Detalle Imagenes",
        "wsp": "3364555555",
        "telefono": "3364555555",
        "direccion": "Detalle 123",
        "ciudad": "San Nicolas",
        "activo": True,
        "usuario_id": 2,
        "id_categoria": 1,
        "imagenes": [
            "https://cloudinary.com/portada.jpg",
            "https://cloudinary.com/segunda.jpg",
        ],
    }

    create_response = client.post(
        "/api/negocios/complete",
        json=data,
        headers=headers_duenio_sin_negocio(client),
    )
    assert create_response.status_code == 201, create_response.text

    slug = create_response.json()["slug"]
    get_response = client.get(f"/api/negocios/slug/{slug}")
    assert get_response.status_code == 200

    imagenes = get_response.json()["imagenes"]
    assert [imagen["url"] for imagen in imagenes] == data["imagenes"]
    assert [imagen["orden"] for imagen in imagenes] == [0, 1]
    assert [imagen["es_portada"] for imagen in imagenes] == [True, False]


def test_listar_negocios_no_devuelve_imagenes(client, seed_data):
    data = {
        "nombre": "Negocio Listado Imagenes",
        "wsp": "3364666666",
        "telefono": "3364666666",
        "direccion": "Listado 123",
        "ciudad": "San Nicolas",
        "activo": True,
        "usuario_id": 2,
        "id_categoria": 1,
        "logo": "https://cloudinary.com/logo-listado.jpg",
        "imagenes": [
            "https://cloudinary.com/listado1.jpg",
        ],
    }

    create_response = client.post(
        "/api/negocios/complete",
        json=data,
        headers=headers_duenio_sin_negocio(client),
    )
    assert create_response.status_code == 201, create_response.text

    list_response = client.get("/api/negocios/")
    assert list_response.status_code == 200

    negocio = next(
        n for n in list_response.json()
        if n["nombre"] == "Negocio Listado Imagenes"
    )
    assert negocio["logo"] == data["logo"]
    assert "imagenes" not in negocio
