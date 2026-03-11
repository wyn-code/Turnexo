from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TurnoBase(BaseModel):
    id_cliente: int
    id_servicio: int
    id_estado: Optional[int] = None
    id_admin: Optional[int] = None
    id_empleado: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None


class Turno(TurnoBase):
    id_turnos: int
    created_at: Optional[datetime] = None
    update_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TurnoCrear(TurnoBase):
    pass


class TurnoActualizar(BaseModel):
    id_cliente: Optional[int] = None
    id_servicio: Optional[int] = None
    id_estado: Optional[int] = None
    id_admin: Optional[int] = None
    id_empleado: Optional[int] = None
    fecha_hora_inicio: Optional[datetime] = None
    fecha_hora_fin: Optional[datetime] = None


class AppointmentResponse(BaseModel):
    """DTO de respuesta para turno/appointment."""
    id_turnos: int
    id_cliente: int
    id_servicio: int
    id_estado: Optional[int] = None
    id_admin: Optional[int] = None
    id_empleado: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None
    created_at: Optional[datetime] = None
    update_at: Optional[datetime] = None

    class Config:
        from_attributes = True
