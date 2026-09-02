from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_negocio
from app.db.session import get_db
from app.models.negocio import Negocio
from app.schemas.appointment_schema import (
    CambiarEstadoTurno,
    TurnoCrear,
    TurnoActualizar,
    TurnoResponse,
    TurnoDisponibilidad,
)
from app.core.estados_turno import CONFIRMADO, COMPLETADO, CANCELADO, NO_ASISTIO, ASISTIO
from app.services.qr_service import validar_token_qr
from app.services.turno_service import (
    listar_turnos,
    obtener_turno_por_id,
    crear_turno,
    actualizar_turno,
    borrar_turno,
    cambiar_estado_turno,
    listar_turnos_por_negocio_y_rango,
    listar_turnos_disponibilidad,
)

router = APIRouter(prefix="/turnos", tags=["Turnos"])


@router.get("/por-rango", response_model=list[TurnoResponse])
def listar_por_rango(
    desde: datetime = Query(..., description="Formato ISO: 2026-04-01T00:00:00"),
    hasta: datetime = Query(..., description="Formato ISO: 2026-05-01T00:00:00"),
    id_empleado: int | None = Query(None),
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    if hasta <= desde:
        raise HTTPException(
            status_code=400,
            detail="'hasta' debe ser mayor que 'desde'",
        )

    return listar_turnos_por_negocio_y_rango(
        db=db,
        id_negocio=negocio.id_negocio,
        desde=desde,
        hasta=hasta,
        id_empleado=id_empleado,
    )


@router.get("/disponibilidad", response_model=list[TurnoDisponibilidad])
def listar_disponibilidad(
    id_negocio: int = Query(...),
    desde: datetime = Query(..., description="Formato ISO: 2026-04-01T00:00:00"),
    hasta: datetime = Query(..., description="Formato ISO: 2026-05-01T00:00:00"),
    id_empleado: int | None = Query(None),
    db: Session = Depends(get_db),
):
    if hasta <= desde:
        raise HTTPException(
            status_code=400,
            detail="'hasta' debe ser mayor que 'desde'",
        )

    return listar_turnos_disponibilidad(
        db=db,
        id_negocio=id_negocio,
        desde=desde,
        hasta=hasta,
        id_empleado=id_empleado,
    )


@router.get("/", response_model=list[TurnoResponse])
def listar(
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    return listar_turnos(db, id_negocio=negocio.id_negocio)

@router.post("/qr/check-in", response_model=TurnoResponse)
def check_in_qr(
    token: str,
    background_tasks: BackgroundTasks,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    payload = validar_token_qr(token)

    if payload["id_negocio"] != negocio.id_negocio:
        raise HTTPException(
            status_code=404,
            detail="Turno no encontrado",
        )

    turno = obtener_turno_por_id(
        db=db,
        turno_id=payload["turno_id"],
        id_negocio=negocio.id_negocio,
    )

    if turno.id_estado == ASISTIO:
        raise HTTPException(
            status_code=400,
            detail="Este turno ya fue registrado como asistido",
        )

    if turno.id_estado != CONFIRMADO:
        raise HTTPException(
            status_code=400,
            detail="Este turno no puede registrarse mediante QR",
        )

    datos = CambiarEstadoTurno(
        id_estado=ASISTIO
    )

    return cambiar_estado_turno(
        db=db,
        turno_id=turno.id_turno,
        datos=datos,
        id_negocio=negocio.id_negocio,
        background_tasks=background_tasks,
    )


@router.get("/{turno_id}", response_model=TurnoResponse)
def obtener(
    turno_id: int,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    return obtener_turno_por_id(
        db,
        turno_id,
        id_negocio=negocio.id_negocio,
    )


@router.post("/", response_model=TurnoResponse, status_code=201)
def crear(turno: TurnoCrear, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return crear_turno(db, turno, background_tasks=background_tasks)


@router.put("/{turno_id}", response_model=TurnoResponse)
def actualizar(
    turno_id: int,
    datos: TurnoActualizar,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    return actualizar_turno(
        db,
        turno_id,
        datos,
        id_negocio=negocio.id_negocio,
    )


@router.delete("/{turno_id}", status_code=204)
def borrar(
    turno_id: int,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    borrar_turno(db, turno_id, id_negocio=negocio.id_negocio)


@router.put("/{turno_id}/estado", response_model=TurnoResponse)
def cambiar_estado(
    turno_id: int,
    datos: CambiarEstadoTurno,
    background_tasks: BackgroundTasks,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    return cambiar_estado_turno(
        db=db,
        turno_id=turno_id,
        datos=datos,
        id_negocio=negocio.id_negocio,
        background_tasks=background_tasks,
    )

