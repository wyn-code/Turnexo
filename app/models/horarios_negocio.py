from sqlalchemy import Column, Time, Integer, ForeignKey
from app.db.base import Base
from sqlalchemy.orm import relationship

class HorarioNegocio(Base):
    __tablename__ = "horarios_negocio"

    id_horarios_negocio = Column(Integer, primary_key=True, index=True)
    id_negocio = Column(
        Integer,
        ForeignKey(
            "negocio.id_negocio",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    dia_semana = Column(Integer, nullable=False)
    hora_apertura = Column(Time, nullable=False)
    hora_cierre = Column(Time, nullable=False)

    negocio = relationship("Negocio", back_populates="horarios")