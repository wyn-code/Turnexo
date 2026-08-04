# georef_service.py
import requests
from sqlalchemy.orm import Session
from app.models.provincia import Provincia
from app.models.localidad import Localidad

BASE_URL = "https://apis.datos.gob.ar/georef/api"


def obtener_provincias(db: Session):
    provincias = db.query(Provincia).order_by(Provincia.nombre).all()
    return [
        {"id_provincia": p.id_provincia, "nombre": p.nombre}
        for p in provincias
    ]


def obtener_localidades(db: Session, id_provincia: int):
    localidades = (
        db.query(Localidad)
        .filter(Localidad.id_provincia == id_provincia)
        .order_by(Localidad.nombre)
        .all()
    )
    return [
        {"id_localidad": l.id_localidad, "nombre": l.nombre}
        for l in localidades
    ]