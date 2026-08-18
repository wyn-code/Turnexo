from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime


class Suscripcion(Base):
    __tablename__ = "suscripciones"


    id_suscripcion = Column(Integer, primary_key=True, index=True)
    id_negocio = Column(
        Integer,
        ForeignKey(
            "negocio.id_negocio",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    id_plan = Column(Integer, ForeignKey("planes.id_plan"), nullable=False)
    estado = Column(String(20), nullable=False, default="activa")
    fecha_inicio = Column(DateTime, default=datetime.now, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    renovacion_automatica = Column(Boolean, default=True)
    proveedor_pago = Column(String(50), nullable=True)
    external_subscription_id = Column(String(150), nullable=True)
    mp_payment_id = Column(String(150), nullable=True, unique=True)

    negocio = relationship(
        "Negocio",
        back_populates="suscripciones",
    )
    plan = relationship("Plan", back_populates="suscripciones")

