import json
import logging
from datetime import datetime, timedelta, timezone
import mercadopago
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import MERCADOPAGO_ACCESS_TOKEN, BACKEND_URL, FRONTEND_URL

logger = logging.getLogger(__name__)
from app.models.negocio import Negocio
from app.models.plan import Plan
from app.models.suscripcion import Suscripcion

sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)


def crear_preferencia_mp(db: Session, negocio: Negocio, plan: Plan) -> dict:
    referencia_externa = f"{negocio.id_negocio}:{plan.id_plan}"

    _token = str(MERCADOPAGO_ACCESS_TOKEN)
    logger.info(
        "MP DIAG: token_prefix=%s client_id=%s",
        _token[:10],
        _token.split("-")[1] if "-" in _token else "?",
    )

    db.query(Suscripcion).filter(
        Suscripcion.id_negocio == negocio.id_negocio,
        Suscripcion.estado == "pendiente",
    ).update({"estado": "cancelada"})
    db.commit()

    preference_data = {
        "items": [
            {
                "title": plan.nombre,
                "quantity": 1,
                "unit_price": float(plan.precio),
                "currency_id": "ARS",
            }
        ],
        "back_urls": {
            "success": f"{FRONTEND_URL.rstrip('/')}/pagos/resultado",
            "failure": f"{FRONTEND_URL.rstrip('/')}/pagos/resultado",
            "pending": f"{FRONTEND_URL.rstrip('/')}/pagos/resultado",
        },
        "auto_return": "approved",
        "notification_url": f"{BACKEND_URL.rstrip('/')}/api/pagos/webhook",
        "external_reference": referencia_externa,
        "date_of_expiration": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }

    logger.info("MP DIAG preference_data: %s", json.dumps(preference_data, ensure_ascii=False))

    try:
        result = sdk.preference().create(preference_data)
    except Exception as exc:
        logger.exception("MP ERROR creando preferencia")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al comunicarse con MercadoPago: {exc}",
        ) from exc

    logger.info("MP DIAG create_response: %s", json.dumps(result, ensure_ascii=False, default=str))

    if result.get("status") not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al crear la preferencia de pago con MercadoPago",
        )

    response = result.get("response")
    if not response or not response.get("id"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="MercadoPago no devolvió una preferencia válida",
        )
    preference_id = response["id"]
    _es_test = str(MERCADOPAGO_ACCESS_TOKEN).startswith("TEST-")
    init_point = (
        response["sandbox_init_point"]
        if _es_test and response.get("sandbox_init_point")
        else response["init_point"]
    )

    logger.info(
        "Preferencia MP creada: collector_id=%s preference_id=%s es_sandbox=%s",
        response.get("collector_id"),
        preference_id,
        "sandbox" in init_point,
    )

    logger.info(
        "MP DIAG preferencia: collector_id=%s preference_id=%s init_point=%s sandbox_init_point=%s",
        response.get("collector_id"),
        preference_id,
        init_point,
        response.get("sandbox_init_point"),
    )

    fecha_inicio = datetime.now()
    fecha_fin = fecha_inicio + timedelta(days=plan.duracion_dias)

    suscripcion = Suscripcion(
        id_negocio=negocio.id_negocio,
        id_plan=plan.id_plan,
        estado="pendiente",
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        renovacion_automatica=True,
        proveedor_pago="mercadopago",
        external_subscription_id=preference_id,
    )
    db.add(suscripcion)
    db.commit()
    db.refresh(suscripcion)

    payload = {
        "init_point": init_point,
        "preference_id": preference_id,
        "collector_id": response.get("collector_id"),
        "sandbox_init_point": response.get("sandbox_init_point"),
    }
    logger.info("MP DIAG return_to_frontend: %s", json.dumps(payload, ensure_ascii=False))
    return payload


def procesar_pago_exitoso(db: Session, negocio_id: int, plan_id: int, preference_id: str) -> Suscripcion:
    suscripcion = (
        db.query(Suscripcion)
        .filter(
            Suscripcion.id_negocio == negocio_id,
            Suscripcion.external_subscription_id == preference_id,
        )
        .first()
    )

    if not suscripcion:
        plan = db.query(Plan).filter(Plan.id_plan == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan no encontrado")

        fecha_inicio = datetime.now()
        fecha_fin = fecha_inicio + timedelta(days=plan.duracion_dias)

        suscripcion = Suscripcion(
            id_negocio=negocio_id,
            id_plan=plan_id,
            estado="activa",
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            renovacion_automatica=True,
            proveedor_pago="mercadopago",
            external_subscription_id=preference_id,
        )
        db.add(suscripcion)
    else:
        suscripcion.estado = "activa"

    db.commit()
    db.refresh(suscripcion)
    return suscripcion


def obtener_suscripcion_actual(db: Session, negocio_id: int) -> Suscripcion | None:
    return (
        db.query(Suscripcion)
        .filter(
            Suscripcion.id_negocio == negocio_id,
        )
        .order_by(Suscripcion.fecha_inicio.desc())
        .first()
    )


def cancelar_suscripcion(db: Session, id_suscripcion: int, negocio_id: int) -> Suscripcion:
    suscripcion = (
        db.query(Suscripcion)
        .filter(
            Suscripcion.id_suscripcion == id_suscripcion,
            Suscripcion.id_negocio == negocio_id,
        )
        .first()
    )

    if not suscripcion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suscripción no encontrada",
        )

    if suscripcion.estado not in ("activa", "pendiente"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cancelar una suscripción en estado '{suscripcion.estado}'",
        )

    suscripcion.estado = "cancelada"
    db.commit()
    db.refresh(suscripcion)
    return suscripcion


def toggle_renovacion_automatica(
    db: Session, id_suscripcion: int, negocio_id: int, activa: bool
) -> Suscripcion:
    suscripcion = (
        db.query(Suscripcion)
        .filter(
            Suscripcion.id_suscripcion == id_suscripcion,
            Suscripcion.id_negocio == negocio_id,
        )
        .first()
    )

    if not suscripcion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suscripción no encontrada",
        )

    suscripcion.renovacion_automatica = activa
    db.commit()
    db.refresh(suscripcion)
    return suscripcion
