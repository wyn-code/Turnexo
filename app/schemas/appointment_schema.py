from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


class TurnoBase(BaseModel):
    id_negocio: int
    id_cliente: int
    id_servicio: int
    id_estado: int
    id_empleado: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None
    id_admin_aprobador: Optional[int] = None
    aprobado_at: Optional[datetime] = None
    rechazado_motivo: Optional[str] = None


class TurnoCrear(BaseModel):
    id_negocio: int
    id_cliente: int
    id_servicio: int
    id_estado: int
    id_empleado: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None

    @model_validator(mode="after")
    def validar_rango_horario(self):
        if (
            self.fecha_hora_fin is not None
            and self.fecha_hora_fin <= self.fecha_hora_inicio
        ):
            raise ValueError(
                "fecha_hora_fin debe ser mayor que fecha_hora_inicio"
            )
        return self


class TurnoActualizar(BaseModel):
    id_negocio: Optional[int] = None
    id_cliente: Optional[int] = None
    id_servicio: Optional[int] = None
    id_estado: Optional[int] = None
    id_empleado: Optional[int] = None
    fecha_hora_inicio: Optional[datetime] = None
    fecha_hora_fin: Optional[datetime] = None
    id_admin_aprobador: Optional[int] = None
    aprobado_at: Optional[datetime] = None
    rechazado_motivo: Optional[str] = None

    @model_validator(mode="after")
    def validar_rango_horario(self):
        if (
            self.fecha_hora_inicio is not None
            and self.fecha_hora_fin is not None
            and self.fecha_hora_fin <= self.fecha_hora_inicio
        ):
            raise ValueError(
                "fecha_hora_fin debe ser mayor que fecha_hora_inicio"
            )
        return self


class TurnoResponse(BaseModel):
    id_turno: int
    id_negocio: int
    id_cliente: int
    id_servicio: int
    id_estado: int
    id_empleado: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: Optional[datetime] = None
    id_admin_aprobador: Optional[int] = None
    aprobado_at: Optional[datetime] = None
    rechazado_motivo: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
