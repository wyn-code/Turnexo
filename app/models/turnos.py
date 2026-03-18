from sqlalchemy import Column, DateTime, ForeignKey, Text, SmallInteger, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Turno(Base):
    __tablename__ = "turno"

    id_turno = Column(BigInteger, primary_key=True, index=True)
    id_negocio = Column(BigInteger, ForeignKey("negocios.id_negocio"), nullable=False)
    id_cliente = Column(BigInteger, ForeignKey("clientes.id_cliente"), nullable=False)
    id_servicio = Column(BigInteger, ForeignKey("servicios.id_servicio"), nullable=False)
    id_estado = Column(SmallInteger, nullable=False)
    id_empleado = Column(BigInteger, ForeignKey("empleados.id_empleado"))
    fecha_hora_inicio = Column(DateTime, nullable=False)
    fecha_hora_fin = Column(DateTime)
    id_admin_aprobador = Column(BigInteger, ForeignKey("usuarios.id_us"))
    aprobado_at = Column(DateTime)
    rechazado_motivo = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    negocio = relationship("Negocio", back_populates="turnos")
    cliente = relationship("Cliente", back_populates="turnos")
    empleado = relationship("Empleado", back_populates="turnos")
    servicio = relationship("Servicio")
    admin_aprobador = relationship("Usuario")