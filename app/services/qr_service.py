import io
import logging
from datetime import datetime, timedelta
import jwt
import qrcode
from fastapi import HTTPException

from app.core.config import FRONTEND_URL, QR_SIGNING_KEY

logger = logging.getLogger(__name__)


def generar_token_qr(
    id_turno: int,
    id_negocio: int,
    fecha_hora_fin: datetime,
) -> str:
    """Generate a signed QR token with expiration.

    fecha_hora_fin llega tz-aware en UTC real (columna timestamptz,
    confirmado con datos en vivo) — no requiere ajuste de timezone.
    """
    exp = fecha_hora_fin + timedelta(hours=3)
    payload = {
        "turno_id": id_turno,
        "id_negocio": id_negocio,
        "exp": exp,  # PyJWT acepta datetime directamente y lo convierte a epoch
    }
    return jwt.encode(payload, QR_SIGNING_KEY, algorithm="HS256")


def validar_token_qr(token: str) -> dict:
    """Validate QR token signature and expiration."""
    try:
        return jwt.decode(token, QR_SIGNING_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=400,
            detail="Este código ya venció, buscá el turno manualmente",
        )
    except jwt.InvalidTokenError as e:
        # Distingue "token trucho" (esperado) de un bug de configuración real
        # (ej. QR_SIGNING_KEY mal seteada en un despliegue nuevo).
        logger.warning(f"Token QR inválido: {e}")
        raise HTTPException(status_code=400, detail="Código QR inválido")


def generar_qr_url(token: str) -> str:
    """Build the scan URL encoded in the QR."""
    return f"{FRONTEND_URL}/dashboard/turnos?token={token}"


def generar_qr_png_bytes(token: str) -> bytes:
    """Generate a QR image from a signed token."""
    payload = generar_qr_url(token)
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()