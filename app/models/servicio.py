from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class Servicio(Base):
    __tablename__ = "servicio"

    id_servicio = Column(Integer, primary_key=True, index=True)
    nombre_servicio = Column(String(30), nullable=False)
    precio = Column(Float, nullable=False)
    requiere_aprobacion = Column(Boolean, index=True)
    duracion_min = Column(Integer)
    duracion_max = Column(Integer)
    activo = Column(Boolean, nullable=False)

    turnos = relationship("Turno", back_populates="servicio")
