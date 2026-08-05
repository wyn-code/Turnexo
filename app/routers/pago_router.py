import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_negocio, get_current_user, get_db
from app.models.negocio import Negocio
from app.models.plan import Plan
from app.models.usuario import Usuario
from app.schemas.plan_schema import (
    CrearPreferenciaRequest,
    CrearPreferenciaResponse,
    RenovacionAutomaticaRequest,
    SuscripcionResponse,
)
from app.services import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pagos", tags=["Pagos"])


@router.post("/crear-preferencia", response_model=CrearPreferenciaResponse)
def crear_preferencia(
    payload: CrearPreferenciaRequest,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id_plan == payload.id_plan).first()
    if not plan or not plan.activo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan no encontrado o inactivo",
        )

    return payment_service.crear_preferencia_mp(db, negocio, plan)


@router.post("/webhook")
async def webhook_mercadopago(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    form_dict = dict(form_data)

    topic = form_dict.get("topic") or request.query_params.get("topic")
    payment_id = form_dict.get("id") or request.query_params.get("id")

    if topic == "payment" and payment_id:
        try:
            payment_response = payment_service.sdk.payment().get(int(payment_id))
            if payment_response["status"] == 200:
                payment = payment_response["response"]
                if payment["status"] == "approved":
                    external_ref = payment.get("external_reference", "")
                    if ":" in external_ref:
                        negocio_id_str, plan_id_str = external_ref.split(":", 1)
                        negocio_id = int(negocio_id_str)
                        plan_id = int(plan_id_str)
                        preference_id = payment.get("preference_id", "")
                        payment_service.procesar_pago_exitoso(
                            db, negocio_id, plan_id, preference_id
                        )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("MP webhook: error procesando payment_id=%s: %s", payment_id, exc)

    return {"status": "ok"}


@router.get("/suscripcion/actual", response_model=SuscripcionResponse | None)
def obtener_suscripcion(
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    return payment_service.obtener_suscripcion_actual(db, negocio.id_negocio)


@router.post("/suscripcion/{id_suscripcion}/cancelar", response_model=SuscripcionResponse)
def cancelar_suscripcion(
    id_suscripcion: int,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    return payment_service.cancelar_suscripcion(db, id_suscripcion, negocio.id_negocio)


@router.put("/suscripcion/{id_suscripcion}/renovacion-automatica", response_model=SuscripcionResponse)
def actualizar_renovacion_automatica(
    id_suscripcion: int,
    payload: RenovacionAutomaticaRequest,
    negocio: Negocio = Depends(get_current_negocio),
    db: Session = Depends(get_db),
):
    return payment_service.toggle_renovacion_automatica(
        db, id_suscripcion, negocio.id_negocio, payload.renovacion_automatica
    )
