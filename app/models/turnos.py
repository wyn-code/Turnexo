from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Turno(Base):
    __tablename__ = "turnos"

    id_turnos = Column(Integer, primary_key=True, index=True)

    id_cliente = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    id_servicio = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    id_estado = Column(Integer, ForeignKey("estados.id"))
    id_admin = Column(Integer, ForeignKey("admins.id"))
    id_empleado = Column(Integer, ForeignKey("empleados.id"))

    fecha_hora_inicio = Column(DateTime, nullable=False)
    fecha_hora_fin = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)
    update_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    cliente = relationship("Cliente")
    servicio = relationship("Servicio")
    estado = relationship("Estado")
    admin = relationship("Admin")
    empleado = relationship("Empleado")