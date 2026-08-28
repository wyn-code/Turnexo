from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.georef_schema import ProvinciaResponse, LocalidadResponse
from app.services.georef_service import (
    obtener_provincias,
    obtener_localidades
)
from typing import Optional

router = APIRouter(
    prefix="/georef",
    tags=["Georef"]
)


@router.get("/provincias", response_model=list[ProvinciaResponse])
def provincias(db: Session = Depends(get_db)):
    return obtener_provincias(db)


@router.get("/localidades", response_model=list[LocalidadResponse])
def localidades(id_provincia: Optional[int] = None, db: Session = Depends(get_db)):
    return obtener_localidades(db, id_provincia)