from tests.auth_helpers import obtener_token


def _seed_geo(db):
    from app.models.provincia import Provincia
    from app.models.localidad import Localidad

    bsas = Provincia(id_provincia=1, nombre="Buenos Aires")
    santa_fe = Provincia(id_provincia=2, nombre="Santa Fe")
    db.add_all([bsas, santa_fe])
    db.flush()

    db.add_all([
        Localidad(id_localidad=1, nombre="San Nicolas", id_provincia=1),
        Localidad(id_localidad=2, nombre="Rosario", id_provincia=2),
    ])
    db.flush()


def test_georef_provincias(client, db):
    _seed_geo(db)

    response = client.get("/api/georef/provincias")
    assert response.status_code == 200

    body = response.json()
    assert {p["nombre"] for p in body} == {"Buenos Aires", "Santa Fe"}
    assert all("id_provincia" in p for p in body)


def test_georef_localidades_filtradas_por_provincia(client, db):
    _seed_geo(db)

    response = client.get(
        "/api/georef/localidades",
        params={"id_provincia": 1},
    )
    assert response.status_code == 200

    body = response.json()
    assert [l["nombre"] for l in body] == ["San Nicolas"]
    assert all(l["id_localidad"] for l in body)


def test_update_negocio_rechaza_localidad_de_otra_provincia(client, db, seed_data):
    _seed_geo(db)
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.put(
        "/api/negocios/1",
        json={
            "id_localidad": 2,  # Rosario pertenece a Santa Fe
            "id_provincia": 1,  # pero se manda Buenos Aires
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "no pertenece" in response.json()["detail"]


def test_update_negocio_sincroniza_ciudad_y_devuelve_nombres(client, db, seed_data):
    _seed_geo(db)
    headers = obtener_token(client, "test1@test.com", "Test1234567!")

    response = client.put(
        "/api/negocios/1",
        json={
            "id_localidad": 1,
            "id_provincia": 1,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["id_localidad"] == 1
    assert body["id_provincia"] == 1
    assert body["localidad_nombre"] == "San Nicolas"
    assert body["provincia_nombre"] == "Buenos Aires"
    assert body["ciudad"] == "San Nicolas"

    me = client.get("/api/negocios/me", headers=headers)
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["id_localidad"] == 1
    assert me_body["id_provincia"] == 1
    assert me_body["localidad_nombre"] == "San Nicolas"
    assert me_body["provincia_nombre"] == "Buenos Aires"
