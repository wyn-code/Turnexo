from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    id_us = Column(Integer, primary_key=True, index=True)
    usuario_us = Column(String(30), nullable=False, unique=True)
    email_us = Column(String(50), nullable=False, unique=True)
    contrasena_us = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
