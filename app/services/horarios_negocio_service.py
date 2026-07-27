from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.horarios_negocio import HorarioNegocio
from app.schemas.horarios_negocio_schema import HorarioNegocioCreate

MAX_FRANJAS_POR_DIA = 2


def _time_to_min(t):
    return t.hour * 60 + t.minute

def _normalized_end_min(apertura: int, cierre: int) -> int:
    """Para slots que cruzan medianoche, sumar 24h al cierre."""
    return cierre + 1440 if cierre <= apertura else cierre

def _validar_horarios(horarios: list[HorarioNegocioCreate], id_negocio_str: str = ""):
    for h in horarios:
        if h.hora_apertura == h.hora_cierre:
            raise HTTPException(
                status_code=400,
                detail=f"La hora de apertura y cierre no pueden ser iguales en {id_negocio_str}",
            )

    agrupados: dict[int, list[HorarioNegocioCreate]] = defaultdict(list)
    for h in horarios:
        agrupados[h.dia_semana].append(h)

    for dia, slots in agrupados.items():
        if len(slots) > MAX_FRANJAS_POR_DIA:
            raise HTTPException(
                status_code=400,
                detail=f"El día {dia} tiene más de {MAX_FRANJAS_POR_DIA} franjas horarias",
            )

        ordenados = sorted(slots, key=lambda x: x.hora_apertura)

        for i in range(len(ordenados) - 1):
            a, b = ordenados[i], ordenados[i + 1]
            cierre_a = _normalized_end_min(
                _time_to_min(a.hora_apertura),
                _time_to_min(a.hora_cierre),
            )
            apertura_b = _time_to_min(b.hora_apertura)

            if cierre_a > apertura_b:
                raise HTTPException(
                    status_code=400,
                    detail=f"Las franjas horarias del día {dia} se superponen",
                )


def crear_horarios(
    db: Session,
    id_negocio: int,
    horarios: list[HorarioNegocioCreate]
):
    _validar_horarios(horarios, f"negocio {id_negocio}")

    for h in horarios:
        nuevo = HorarioNegocio(
            id_negocio=id_negocio,
            dia_semana=h.dia_semana,
            hora_apertura=h.hora_apertura,
            hora_cierre=h.hora_cierre
        )
        db.add(nuevo)

    db.commit()
    return {"message": "Horarios guardados correctamente"}


def obtener_horarios_por_negocio(
    db: Session,
    id_negocio: int
):
    horarios = db.query(HorarioNegocio).filter(
        HorarioNegocio.id_negocio == id_negocio
    ).all()

    if not horarios:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron horarios para este negocio"
        )

    return horarios


def actualizar_horarios(
    db: Session,
    id_negocio: int,
    horarios: list[HorarioNegocioCreate]
):
    existentes = db.query(HorarioNegocio).filter(
        HorarioNegocio.id_negocio == id_negocio
    ).all()

    if not existentes:
        raise HTTPException(
            status_code=404,
            detail="No existen horarios para actualizar"
        )

    _validar_horarios(horarios, f"negocio {id_negocio}")

    db.query(HorarioNegocio).filter(
        HorarioNegocio.id_negocio == id_negocio
    ).delete()

    for h in horarios:
        nuevo = HorarioNegocio(
            id_negocio=id_negocio,
            dia_semana=h.dia_semana,
            hora_apertura=h.hora_apertura,
            hora_cierre=h.hora_cierre
        )
        db.add(nuevo)

    db.commit()

    return {"message": "Horarios actualizados correctamente"}


def eliminar_horarios(
    db: Session,
    id_negocio: int
):
    horarios = db.query(HorarioNegocio).filter(
        HorarioNegocio.id_negocio == id_negocio
    ).all()

    if not horarios:
        raise HTTPException(
            status_code=404,
            detail="No existen horarios para eliminar"
        )

    db.query(HorarioNegocio).filter(
        HorarioNegocio.id_negocio == id_negocio
    ).delete()

    db.commit()

    return {"message": "Horarios eliminados correctamente"}
