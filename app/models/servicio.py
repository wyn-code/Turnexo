from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Servicio(Base):
    __tablename__ = "servicio"

    id_servicio = Column(Integer, primary_key=True, index=True)
    id_negocio = Column(
    Integer,
    ForeignKey(
        "negocio.id_negocio",
        ondelete="CASCADE",
    ),
    nullable=False,
)

    nombre_servicio = Column(String(30), nullable=False)
    precio = Column(Float, nullable=False)
    requiere_aprobacion = Column(Boolean, index=True)
    duracion_min = Column(Integer, nullable=False)
    duracion_max = Column(Integer, nullable=False)
    activo = Column(Boolean, nullable=False)

    negocio = relationship(
        "Negocio",
        back_populates="servicios",
    )
    turnos = relationship(
        "Turno",
        back_populates="servicio",
        passive_deletes=True,
    )