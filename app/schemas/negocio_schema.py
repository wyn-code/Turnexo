from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.horarios_negocio_schema import HorarioNegocioCreate, HorarioNegocioResponse
from app.schemas.servicio_schema import (
    ServicioCreateNested,
    ServicioResponse
)

from app.schemas.empleado_schema import (
    EmpleadoCreate,
    EmpleadoResponse
)

from app.schemas.categoria_schema import (
    CategoriaResponse
)


class NegocioBase(BaseModel):
    nombre: str
    id_categoria: int
    wsp: str
    telefono: Optional[str] = None
    direccion: str
    ciudad: str
    id_localidad: Optional[int] = None
    id_provincia: Optional[int] = None
    ig_url: Optional[str] = None
    logo: Optional[str] = None
    descripcion: str = ""
    activo: bool = True


class NegocioCreate(NegocioBase):
    usuario_id: int | None = None


class NegocioImagenResponse(BaseModel):
    id_imagen: int
    url: str
    es_portada: bool
    orden: int
    model_config = ConfigDict(from_attributes=True)


class NegocioListResponse(BaseModel):
    id_negocio: int
    usuario_id: int
    nombre: str
    wsp: str
    telefono: str | None = None
    direccion: str
    ciudad: str
    id_localidad: int | None = None
    id_provincia: int | None = None
    localidad_nombre: str | None = None
    provincia_nombre: str | None = None
    latitud: float | None
    longitud: float | None
    slug: str
    ig_url: str | None = None
    logo: str | None = None
    descripcion: str | None = None
    activo: bool
    id_categoria: int
    categoria: CategoriaResponse | None
    horarios: list[HorarioNegocioResponse] = Field(default_factory=list)
    tiene_mapa: bool = False
    model_config = ConfigDict(from_attributes=True)


class NegocioResponse(NegocioListResponse):
    imagenes: list[NegocioImagenResponse] = Field(default_factory=list)


class NegocioCompleteCreate(NegocioCreate):
    imagenes: list[str] = Field(default_factory=list)
    servicios: list[ServicioCreateNested] = Field(default_factory=list)
    empleados: list[EmpleadoCreate] = Field(default_factory=list)
    horarios: list[HorarioNegocioCreate] = Field(default_factory=list)


class NegocioCompleteResponse(
    NegocioResponse
):
    servicios: List[ServicioResponse] = (Field(default_factory=list))
    empleados: List[EmpleadoResponse] = (Field(default_factory=list))
    horarios: List[HorarioNegocioResponse] = Field(default_factory=list)


class NegocioUpdate(BaseModel):
    nombre: str | None = None
    wsp: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    ig_url: str | None = None
    logo: str | None = None
    descripcion: str | None = None
    imagenes: list[str] | None = None
    id_categoria: int | None = None
    id_localidad: int | None = None
    id_provincia: int | None = None
    activo: bool | None = None


class DuenioResponse(BaseModel):
    nombre: str
    email: str
    model_config = ConfigDict(from_attributes=True)


class NegocioAdminResponse(BaseModel):
    id_negocio: int
    nombre: str
    wsp: str | None
    telefono: str | None
    direccion: str | None
    ciudad: str | None
    ig_url: str | None
    activo: bool
    slug: str

    duenio: DuenioResponse

    model_config = ConfigDict(from_attributes=True)


class NegocioMapaResponse(BaseModel):
    id_negocio: int
    nombre: str
    latitud: float | None
    longitud: float | None
    model_config = ConfigDict(from_attributes=True)
