import hashlib
import hmac
import logging
import time as time_module

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import MERCADOPAGO_ACCESS_TOKEN
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


def _validar_firma_mp(request: Request, payment_id: str) -> bool:
    """Valida la firma del webhook de Mercado Pago.

    Formato v2: headers `x-signature: ts=<ts>,v1=<hash>` y `x-request-id`.
    La firma es HMAC-SHA256(access_token, "id:{id};request-id:{rid};ts:{ts}").
    Formato legacy (deprecado): query param `signature` = HMAC(access_token, "id:{id}").
    """
    x_signature = request.headers.get("x-signature") or request.headers.get("signature")
    x_request_id = request.headers.get("x-request-id") or request.headers.get("request-id")

    if not x_signature:
        return False

    legacy = request.query_params.get("signature")
    if not x_request_id and legacy and "=" not in x_signature:
        expected = hmac.new(
            MERCADOPAGO_ACCESS_TOKEN.encode(),
            f"id:{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, legacy)

    if not x_request_id:
        return False

    params = {}
    for part in x_signature.split(","):
        if "=" in part:
            key, _, value = part.partition("=")
            params[key.strip()] = value.strip()

    ts = params.get("ts")
    v1 = params.get("v1")
    if not ts or not v1:
        return False

    try:
        if abs(int(time_module.time()) - int(ts)) > 300:
            return False
    except ValueError:
        return False

    manifest = f"id:{payment_id};request-id:{x_request_id};ts:{ts}"
    expected = hmac.new(
        MERCADOPAGO_ACCESS_TOKEN.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, v1)


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

    if not payment_id:
        return {"status": "ok"}

    if not _validar_firma_mp(request, str(payment_id)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma de webhook inválida",
        )

    if topic == "payment":
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
                            db,
                            negocio_id,
                            plan_id,
                            preference_id,
                            str(payment_id),
                        )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("MP webhook: error procesando payment_id=%s: %s", payment_id, exc)

    elif topic == "subscription":
        try:
            payment_service.procesar_subscripcion_mp(db, str(payment_id))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception(
                "MP webhook: error procesando subscription_id=%s: %s",
                payment_id,
                exc,
            )

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
