from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UsuarioBase(BaseModel):
    usuario_us: str
    email_us: EmailStr


class UsuarioCreate(UsuarioBase):
    contraseña_us: str


class UsuarioUpdate(BaseModel):
    usuario_us: Optional[str] = None
    email_us: Optional[EmailStr] = None
    contraseña_us: Optional[str] = None


class UsuarioResponse(UsuarioBase):
    id_us: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True