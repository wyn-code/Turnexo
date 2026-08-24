from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, func
from sqlalchemy.sql import functions

from app.db.base import Base


class Empleado(Base):
    __tablename__ = "empleado"

    id_empleado = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(30), nullable=False)
    apellido = Column(String(30), nullable=False)
    telefono = Column(String(30), unique=True, nullable=True)
    activo = Column(Boolean, nullable=False)
    calendario_token = Column(String(64), unique=True, nullable=True)
    calendario_token_revoked_at = Column(DateTime(timezone=True), nullable=True)
    calendario_enviado_at = Column(DateTime(timezone=True), nullable=True)
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