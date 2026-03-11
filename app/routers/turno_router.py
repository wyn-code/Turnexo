from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.schemas.appointment_schema import (
    TurnoCrear,
    TurnoActualizar,
    AppointmentResponse,
)
from app.services.turno_service import (
    listar_turnos,
    obtener_turno_por_id,
    crear_turno,
    actualizar_turno,
    borrar_turno,
)

router = APIRouter(prefix="/turnos", tags=["Turnos"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[AppointmentResponse])
def listar(db: Session = Depends(get_db)):
    return listar_turnos(db)


@router.get("/{turno_id}", response_model=AppointmentResponse)
def obtener(turno_id: int, db: Session = Depends(get_db)):
    turno = obtener_turno_por_id(db, turno_id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return turno


@router.post("/", response_model=AppointmentResponse)
def crear(turno: TurnoCrear, db: Session = Depends(get_db)):
    return crear_turno(db, turno)


@router.put("/{turno_id}", response_model=AppointmentResponse)
def actualizar(turno_id: int, datos: TurnoActualizar, db: Session = Depends(get_db)):
    turno = actualizar_turno(db, turno_id, datos)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return turno


@router.delete("/{turno_id}")
def borrar(turno_id: int, db: Session = Depends(get_db)):
    turno = borrar_turno(db, turno_id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return {"mensaje": "Turno eliminado"}
