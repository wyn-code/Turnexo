from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_negocio, get_db

from app.schemas.plan_schema import NegocioFuncionesResponse, PlanResponse
from app.services import plan_service
from app.models.plan import Plan
from app.models.negocio import Negocio

router = APIRouter(prefix="/planes", tags=["Planes"])


@router.get("/", response_model=list[PlanResponse])
def listar_planes(db: Session = Depends(get_db)):
    return db.query(Plan).options(selectinload(Plan.funciones)).filter(Plan.activo == True).all()


@router.get("/negocios/{id_negocio}/funciones", response_model=NegocioFuncionesResponse)
def obtener_funciones_negocio(
    id_negocio: int,
    db: Session = Depends(get_db),
    negocio: Negocio = Depends(get_current_negocio),
):
    if negocio.id_negocio != id_negocio:
        raise HTTPException(status_code=403, detail="No tenés acceso a este negocio")

    suscripcion = plan_service.obtener_suscripcion_activa(id_negocio, db)
    funciones = plan_service.obtener_funciones_negocio(id_negocio, db)

    return NegocioFuncionesResponse(
        id_negocio=id_negocio,
        plan=suscripcion.plan.nombre if suscripcion else None,
        estado=suscripcion.estado if suscripcion else None,
        fecha_fin=suscripcion.fecha_fin if suscripcion else None,
        funciones=funciones,
    )