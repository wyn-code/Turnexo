from sqlalchemy.orm import Session

from app.models.empleado import Empleado
from app.schemas.empleado_schema import EmpleadoCreate


def ver_empleados(db: Session):
    return db.query(Empleado).all()


def ver_empleado_por_id(db: Session, empleado_id: int):
    return db.query(Empleado).filter(Empleado.id_empleado == empleado_id).first()


def crear_empleado(db: Session, empleado: EmpleadoCreate):
    nuevo_empleado = Empleado(
        nombre=empleado.nombre,
        apellido=empleado.apellido,
        telefono=empleado.telefono,
        activo=empleado.activo,
    )
    db.add(nuevo_empleado)
    db.commit()
    db.refresh(nuevo_empleado)
    return nuevo_empleado
