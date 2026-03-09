from sqlalchemy import Column, Integer, String, Float, Boolean
from app.db.base import Base

class Service(Base):
    __tablename__ = "servicio"

    id_servicio = Column(Integer, primary_key=True, index=True)
    nombre_sv = Column(String(30), nullable=False)
    precio_sv = Column(Float(30), nullable=False)
    aprobacion_sv = Column(Boolean, unique=True, index=True)
    duracion_min = Column(Integer)
    duracion_max = Column(Integer)
    activo = Column(Boolean, nullable=False)