from pydantic import BaseModel, ConfigDict


class ProvinciaResponse(BaseModel):
    id_provincia: int
    nombre: str
    model_config = ConfigDict(from_attributes=True)


class LocalidadResponse(BaseModel):
    id_localidad: int
    nombre: str
    model_config = ConfigDict(from_attributes=True)
