from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class Negocio(Base):
    __tablename__ = "negocio"
    id_ng = Column(Integer, primary_key=True, index=True)
    rubro = Column(String(30), nullable=False)
    telefono_ng = Column(String(30), nullable=False)
    direccion_ng = Column(String(30), nullable=False)
    ig_url = Column(String)
    facebook_url = Column(String)
    logo = Column(String)
    created_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)    