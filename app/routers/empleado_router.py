from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.negocio import Negocio
from app.models.usuario import Usuario

from app.schemas.empleado_schema import EmpleadoCreate, EmpleadoResponse
from app.services.empleado_service import (
    crear_empleado,
    ver_empleado_por_id,
    ver_empleados,
)

router = APIRouter(prefix="/empleados", tags=["Empleados"])


@router.get("/", response_model=list[EmpleadoResponse])
def listar(
    id_negocio: int = Query(...),
    db: Session = Depends(get_db),
):
    return ver_empleados(db, id_negocio=id_negocio)


@router.get("/{empleado_id}", response_model=EmpleadoResponse)
def obtener(
    empleado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    empleado = ver_empleado_por_id(db, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    if (
        empleado.negocio.usuario_id != current_user.id_us
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver este empleado",
        )
    return empleado


@router.post("/", response_model=EmpleadoResponse)
def crear(
    empleado: EmpleadoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    negocio = (
        db.query(Negocio)
        .filter(Negocio.id_negocio == empleado.id_negocio)
        .first()
    )
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    if negocio.usuario_id != current_user.id_us:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para agregar empleados a este negocio",
        )

    return crear_empleado(db, empleado)