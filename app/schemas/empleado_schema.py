from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class EmpleadoBase(BaseModel):
    nombre: str
    apellido: str
    telefono: Optional[str] = None
    activo: bool = True


class EmpleadoCreate(EmpleadoBase):
    id_negocio: int


class EmpleadoCreateNested(EmpleadoBase):
    pass


class EmpleadoResponse(EmpleadoBase):
    id_empleado: int
    id_negocio: int

    model_config = ConfigDict(from_attributes=True)


class GenerarCalendarioRequest(BaseModel):
    email: EmailStr


class EmpleadoCalendarioResponse(BaseModel):
    id_empleado: int
    calendario_link: Optional[str] = None
    calendario_enviado_at: Optional[datetime] = None


EmpleadoCalendarioEstado = Literal["sin_calendario", "activo", "revocado"]


class EmpleadoCalendarioEstadoResponse(BaseModel):
    id_empleado: int
    estado: EmpleadoCalendarioEstado
    calendario_enviado_at: Optional[datetime] = None