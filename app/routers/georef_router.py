from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.georef_service import (
    obtener_provincias,
    obtener_localidades
)
from app.services.mapbox_service import obtener_coordenadas

router = APIRouter(
    prefix="/georef",
    tags=["Georef"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/provincias")
def provincias(db: Session = Depends(get_db)):
    return obtener_provincias(db)


@router.get("/localidades")
def localidades(id_provincia: int, db: Session = Depends(get_db)):
    return obtener_localidades(db, id_provincia)


@router.get("/test-geocoding")
def test_geocoding():
    return obtener_coordenadas(
        "Av. Corrientes 1234",
        "Buenos Aires",
        "Buenos Aires",
    )