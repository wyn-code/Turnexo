from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.db.base import Base
from sqlalchemy.orm import relationship


class Empleado(Base):
    __tablename__ = "empleado"

    id_empleado = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(30), nullable=False)
    apellido = Column(String(30), nullable=False)
    telefono = Column(String(30), unique=True, nullable=False)
    activo = Column(Boolean, nullable=False)

    turnos = relationship("Turno", back_populates="empleado")