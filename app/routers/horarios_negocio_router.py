# app/routers/horario_negocio_router.py

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.core.dependencies import get_current_negocio
from app.db.session import get_db
from app.models.negocio import Negocio
from app.schemas.horarios_negocio_schema import HorarioNegocioCreate
from app.services.horarios_negocio_service import (
    crear_horarios,
    obtener_horarios_por_negocio,
    actualizar_horarios,
    eliminar_horarios
)

router = APIRouter(
    prefix="/horarios",
    tags=["Horarios"]
)


def _verificar_propiedad(id_negocio: int, negocio: Negocio) -> None:
    if negocio.id_negocio != id_negocio:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos sobre este negocio",
        )


@router.post("/{id_negocio}")
def crear(
    id_negocio: int,
    horarios: list[HorarioNegocioCreate],
    db: Session = Depends(get_db),
    negocio: Negocio = Depends(get_current_negocio),
):
    _verificar_propiedad(id_negocio, negocio)
    return crear_horarios(db, id_negocio, horarios)


@router.get("/{id_negocio}")
def obtener(
    id_negocio: int,
    db: Session = Depends(get_db)
):
    return obtener_horarios_por_negocio(db, id_negocio)


@router.put("/{id_negocio}")
def actualizar(
    id_negocio: int,
    horarios: list[HorarioNegocioCreate],
    db: Session = Depends(get_db),
    negocio: Negocio = Depends(get_current_negocio),
):
    _verificar_propiedad(id_negocio, negocio)
    return actualizar_horarios(db, id_negocio, horarios)


@router.delete("/{id_negocio}")
def eliminar(
    id_negocio: int,
    db: Session = Depends(get_db),
    negocio: Negocio = Depends(get_current_negocio),
):
    _verificar_propiedad(id_negocio, negocio)
    return eliminar_horarios(db, id_negocio)