from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey

from app.db.base import Base


class Empleado(Base):
    __tablename__ = "empleado"

    id_empleado = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(30), nullable=False)
    apellido = Column(String(30), nullable=False)
    telefono = Column(String(30), unique=True, nullable=True)
    activo = Column(Boolean, nullable=False)
    id_negocio = Column(
    Integer,
    ForeignKey(
        "negocio.id_negocio",
        ondelete="CASCADE",
    ),
    nullable=False,
)
    
    negocio = relationship(
        "Negocio",
        back_populates="empleados",
    )
    turnos = relationship(
        "Turno",
        back_populates="empleado",
        passive_deletes=True,
    )