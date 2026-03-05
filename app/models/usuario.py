from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id_us = Column(Integer, primary_key=True, index=True)
    usuario_us = Column(String(30), nullable=False, unique=True)
    email_us = Column(String(50), nullable=False, unique=True)
    contraseña_us = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)