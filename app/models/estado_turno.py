from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.db.base import Base


class EstadoTurno(Base):
    __tablaname__ = "estado_turno"
    id_estado = Column(Integer, primary_key=True, index=True)
    nombre_estado = Column(String(30), nullable=False)