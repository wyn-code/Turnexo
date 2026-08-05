from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal


class PlanResponse(BaseModel):
    id_plan: int
    nombre: str
    precio: float
    duracion_dias: int
    descripcion: str | None = None
    activo: bool
    model_config = ConfigDict(from_attributes=True)
    feature_keys: list[str]


class SuscripcionResponse(BaseModel):
    id_suscripcion: int
    estado: str
    fecha_inicio: datetime
    fecha_fin: datetime
    renovacion_automatica: bool
    plan: PlanResponse
    model_config = ConfigDict(from_attributes=True)


class NegocioFuncionesResponse(BaseModel):
    id_negocio: int
    plan: str | None          
    estado: str | None        
    fecha_fin: datetime | None
    funciones: list[str]


# ─── Pagos / MercadoPago ──────────────────────────────────────────────

class CrearPreferenciaRequest(BaseModel):
    id_plan: int


class CrearPreferenciaResponse(BaseModel):
    init_point: str
    preference_id: str


class RenovacionAutomaticaRequest(BaseModel):
    renovacion_automatica: bool      