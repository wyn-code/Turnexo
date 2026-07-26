from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.models.estado_turno import EstadoTurno


class Turno(Base):
    __tablename__ = "turno"

    id_turno = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_negocio = Column(
        Integer,
        ForeignKey(
            "negocio.id_negocio",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    id_servicio = Column(
        Integer,
        ForeignKey(
            "servicio.id_servicio",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    id_empleado = Column(
        Integer,
        ForeignKey(
            "empleado.id_empleado",
            ondelete="CASCADE",
        ),
    )
    id_cliente = Column(Integer, ForeignKey("cliente.id_cliente"), nullable=False)
    id_estado = Column(Integer, ForeignKey('estado_turno.id_estado'), nullable=False)
    fecha_hora_inicio = Column(DateTime, nullable=False)
    fecha_hora_fin = Column(DateTime)
    rechazado_motivo = Column(Text)
    recordatorio_enviado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    negocio = relationship(
        "Negocio",
        back_populates="turnos",
    )
    cliente = relationship("Cliente", back_populates="turnos")
    empleado = relationship("Empleado", back_populates="turnos")
    servicio = relationship("Servicio", back_populates="turnos")
    estado = relationship("EstadoTurno")
