from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.schemas.empleado_schema import EmpleadoCreate, EmpleadoResponse
from app.services.empleado_service import (
    crear_empleado,
    ver_empleado_por_id,
    ver_empleados,
)

router = APIRouter(prefix="/empleados", tags=["Empleados"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[EmpleadoResponse])
def listar(db: Session = Depends(get_db)):
    return ver_empleados(db)


@router.get("/{empleado_id}", response_model=EmpleadoResponse)
def obtener(empleado_id: int, db: Session = Depends(get_db)):
    empleado = ver_empleado_por_id(db, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado


@router.post("/", response_model=EmpleadoResponse)
def crear(empleado: EmpleadoCreate, db: Session = Depends(get_db)):
    return crear_empleado(db, empleado)

