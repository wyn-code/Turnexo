from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EmpleadoBase(BaseModel):
    nombre: str
    apellido: str
    telefono: str
    activo: bool


class EmpleadoCreate(EmpleadoBase):
    pass


class EmpleadoResponse(EmpleadoBase):
    id_empleado: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

