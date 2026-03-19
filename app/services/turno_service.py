from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.turnos import Turno
from app.schemas.appointment_schema import TurnoCrear, TurnoActualizar
from app.models.servicio import Servicio


def listar_turnos(db: Session):
    return db.query(Turno).all()


def obtener_turno_por_id(db: Session, turno_id: int):
    return db.query(Turno).filter(Turno.id_turno == turno_id).first()


# 🔥 Validación de solapamiento
def hay_superposicion(db: Session, id_empleado: int, inicio, fin, excluir_turno_id=None):
    query = db.query(Turno).filter(
        Turno.id_empleado == id_empleado,
        Turno.fecha_hora_inicio < fin,
        Turno.fecha_hora_fin > inicio
    )

    # Para updates (evitar compararse consigo mismo)
    if excluir_turno_id:
        query = query.filter(Turno.id_turno != excluir_turno_id)

    return query.first() is not None


def crear_turno(db: Session, turno: TurnoCrear):
    servicio = db.query(Servicio).filter(
        Servicio.id_servicio == turno.id_servicio
    ).first()

    if not servicio:
        raise HTTPException(
            status_code=404,
            detail="El servicio no existe"
        )

    # ⏱ Calcular fecha_fin si no viene
    fecha_hora_fin = turno.fecha_hora_fin
    if fecha_hora_fin is None:
        fecha_hora_fin = turno.fecha_hora_inicio + timedelta(
            minutes=servicio.duracion_min
        )

    # 🛑 Validación básica
    if fecha_hora_fin <= turno.fecha_hora_inicio:
        raise HTTPException(
            status_code=400,
            detail="La fecha_hora_fin debe ser mayor que la fecha_hora_inicio"
        )

    # 🔥 Validación de solapamiento (ANTES de DB)
    if hay_superposicion(
        db,
        turno.id_empleado,
        turno.fecha_hora_inicio,
        fecha_hora_fin
    ):
        raise HTTPException(
            status_code=409,
            detail="El empleado ya tiene un turno en ese horario"
        )

    nuevo_turno = Turno(
        id_negocio=turno.id_negocio,
        id_cliente=turno.id_cliente,
        id_servicio=turno.id_servicio,
        id_estado=turno.id_estado,
        id_empleado=turno.id_empleado,
        fecha_hora_inicio=turno.fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        id_admin_aprobador=None,
        aprobado_at=None,
        rechazado_motivo=None
    )

    try:
        db.add(nuevo_turno)
        db.commit()
        db.refresh(nuevo_turno)
        return nuevo_turno

    except IntegrityError as e:
        db.rollback()

        # 🔥 Defensa extra (por si falla la validación previa)
        if "ex_turno_no_solapa_por_empleado" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail="El empleado ya tiene un turno en ese horario"
            )

        raise HTTPException(
            status_code=400,
            detail="Error de integridad en la base de datos"
        )


def actualizar_turno(db: Session, turno_id: int, datos: TurnoActualizar):
    turno_db = db.query(Turno).filter(Turno.id_turno == turno_id).first()

    if not turno_db:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    nueva_fecha_inicio = (
        datos.fecha_hora_inicio
        if datos.fecha_hora_inicio is not None
        else turno_db.fecha_hora_inicio
    )

    nueva_fecha_fin = (
        datos.fecha_hora_fin
        if datos.fecha_hora_fin is not None
        else turno_db.fecha_hora_fin
    )

    # 🛑 Validación básica
    if nueva_fecha_fin is not None and nueva_fecha_fin <= nueva_fecha_inicio:
        raise HTTPException(
            status_code=400,
            detail="La fecha_hora_fin debe ser mayor que la fecha_hora_inicio"
        )

    # 🔥 Validación de solapamiento en update
    if hay_superposicion(
        db,
        datos.id_empleado if datos.id_empleado else turno_db.id_empleado,
        nueva_fecha_inicio,
        nueva_fecha_fin,
        excluir_turno_id=turno_id
    ):
        raise HTTPException(
            status_code=409,
            detail="El empleado ya tiene un turno en ese horario"
        )

    # 🔄 Actualización de campos
    if datos.id_negocio is not None:
        turno_db.id_negocio = datos.id_negocio
    if datos.id_cliente is not None:
        turno_db.id_cliente = datos.id_cliente
    if datos.id_servicio is not None:
        turno_db.id_servicio = datos.id_servicio
    if datos.id_estado is not None:
        turno_db.id_estado = datos.id_estado
    if datos.id_empleado is not None:
        turno_db.id_empleado = datos.id_empleado
    if datos.fecha_hora_inicio is not None:
        turno_db.fecha_hora_inicio = datos.fecha_hora_inicio
    if datos.fecha_hora_fin is not None:
        turno_db.fecha_hora_fin = datos.fecha_hora_fin
    if datos.id_admin_aprobador is not None:
        turno_db.id_admin_aprobador = datos.id_admin_aprobador
    if datos.aprobado_at is not None:
        turno_db.aprobado_at = datos.aprobado_at
    if datos.rechazado_motivo is not None:
        turno_db.rechazado_motivo = datos.rechazado_motivo

    try:
        db.commit()
        db.refresh(turno_db)
        return turno_db

    except IntegrityError as e:
        db.rollback()

        if "ex_turno_no_solapa_por_empleado" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail="El empleado ya tiene un turno en ese horario"
            )

        raise HTTPException(
            status_code=400,
            detail="Error de integridad en la base de datos"
        )


def borrar_turno(db: Session, turno_id: int):
    turno_db = db.query(Turno).filter(Turno.id_turno == turno_id).first()

    if not turno_db:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    try:
        db.delete(turno_db)
        db.commit()
        return turno_db

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al eliminar el turno"
        )