from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class Usuario(Base):
    __tablename__ = "cliente"

    id_cliente = Column(Integer, primary_key=True, index=True)
    telefono_clt = Column(String(30), nullable=False, unique=True)
    nombre_clt = Column(String(30), nullable=False)
    apellido_clt = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)