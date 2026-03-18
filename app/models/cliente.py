from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Cliente(Base):
    __tablename__ = "clientes"
    id_cliente = Column(BigInteger, primary_key=True, index=True)
    telefono_clt = Column(String(30), nullable=False, unique=True)
    nombre_clt = Column(String(30), nullable=False)
    apellido_clt = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    turnos = relationship("Turno", back_populates="cliente")