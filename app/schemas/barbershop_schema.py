from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class NegocioBase(BaseModel):
    rubro: str
    telefono_ng: str
    direccion_ng: str
    ig_url: Optional[str] = None
    facebook_url: Optional[str] = None
    logo: Optional[str] = None


class NegocioCreate(NegocioBase):
    pass


class NegocioUpdate(BaseModel):
    rubro: Optional[str] = None
    telefono_ng: Optional[str] = None
    direccion_ng: Optional[str] = None
    ig_url: Optional[str] = None
    facebook_url: Optional[str] = None
    logo: Optional[str] = None


class NegocioResponse(NegocioBase):
    id_ng: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True