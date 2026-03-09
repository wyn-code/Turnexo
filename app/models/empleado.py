from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.db.base import Base


class Service(Base):
    __tablaname__ = "empleado"
    id_empleado = Column(Integer, primary_key=True, index=True)
    nombre_empleado = Column(String(30), nullable=False)
    apellido_empleado = Column(String(30), nullable=False)
    telefono_empleado = Column(String(30), unique=True, nullable=False)
    activo_empleado = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
