# georef_service.py
from typing import Optional
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


def obtener_localidades(db: Session, id_provincia: Optional[int] = None):
    query = db.query(Localidad)
    if id_provincia is not None:
        query = query.filter(Localidad.id_provincia == id_provincia)
    return [
        {"id_localidad": l.id_localidad, "nombre": l.nombre}
        for l in query.order_by(Localidad.nombre).all()
    ]