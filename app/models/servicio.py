from sqlalchemy import Column, Integer, String, Float, Boolean
from app.db.base import Base

class Servicio(Base):
    __tablename__ = "servicios"

    id_servicio = Column(Integer, primary_key=True, index=True)
    nombre_sv = Column(String(30), nullable=False)
    precio_sv = Column(Float, nullable=False)
    aprobacion_sv = Column(Boolean, index=True)
    duracion_min = Column(Integer)
    duracion_max = Column(Integer)
    activo = Column(Boolean, nullable=False)