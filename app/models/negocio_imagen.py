from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class NegocioImagen(Base):
    __tablename__ = "negocio_imagen"

    id_imagen = Column(Integer, primary_key=True, index=True)
    id_negocio = Column(
        Integer,
        ForeignKey("negocio.id_negocio", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(String(500), nullable=False)
    es_portada = Column(Boolean, default=False, nullable=False)
    orden = Column(Integer, default=0, nullable=False)

    negocio = relationship(
        "Negocio",
        back_populates="imagenes",
    )
