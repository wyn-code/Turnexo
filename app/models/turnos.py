from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

from app.models.cliente import Cliente

class Turno(Base):
    __tablename__ = "turnos"

    id_turnos = Column(Integer, primary_key=True, index=True)

    id_cliente = Column(Integer, ForeignKey("clientes.id"), nullable=False)

    fecha_hora_inicio = Column(DateTime, nullable=False)
    fecha_hora_fin = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)

    cliente = relationship("Cliente", back_populates="turnos")