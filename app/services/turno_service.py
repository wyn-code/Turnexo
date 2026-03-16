from sqlalchemy.orm import Session

from app.models.turnos import Turno
from app.schemas.appointment_schema import TurnoCrear, TurnoActualizar


def listar_turnos(db: Session):
    return db.query(Turno).all()


def obtener_turno_por_id(db: Session, turno_id: int):
    return db.query(Turno).filter(Turno.id_turnos == turno_id).first()


def crear_turno(db: Session, turno: TurnoCrear):
    nuevo_turno = Turno(
        id_cliente=turno.id_cliente,
        id_servicio=turno.id_servicio,
        id_estado=turno.id_estado,
        # id_empleado=turno.id_empleado,
        fecha_hora_inicio=turno.fecha_hora_inicio,
        fecha_hora_fin=turno.fecha_hora_fin,
    )
    db.add(nuevo_turno)
    db.commit()
    db.refresh(nuevo_turno)
    return nuevo_turno


def actualizar_turno(db: Session, turno_id: int, datos: TurnoActualizar):
    turno_db = db.query(Turno).filter(Turno.id_turnos == turno_id).first()

    if not turno_db:
        return None

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

    db.commit()
    db.refresh(turno_db)
    return turno_db


def borrar_turno(db: Session, turno_id: int):
    turno_db = db.query(Turno).filter(Turno.id_turnos == turno_id).first()

    if not turno_db:
        return None

    db.delete(turno_db)
    db.commit()
    return turno_db
