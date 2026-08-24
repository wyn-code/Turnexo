from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.empleado import Empleado
from app.models.negocio import Negocio
from app.models.usuario import Usuario
from app.schemas.empleado_schema import (
    GenerarCalendarioRequest,
    EmpleadoCalendarioResponse,
    EmpleadoCalendarioEstadoResponse,
)
from app.services.empleado_calendario_service import (
    obtener_o_crear_token,
    obtener_estado_calendario,
    revocar_token,
    generar_ics,
    enviar_link_por_email,
)

router = APIRouter(prefix="/negocios", tags=["Empleados Calendario"])


def _verificar_due_o_admin(db, current_user: Usuario, negocio_id: int):
    negocio = db.query(Negocio).filter(Negocio.id_negocio == negocio_id).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    if negocio.usuario_id != current_user.id_us and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para gestionar calendarios de este negocio",
        )
    return negocio


# --- Endpoints dueño / admin ---

@router.post(
    "/{negocio_id}/empleados/{id_empleado}/generar-calendario",
    response_model=EmpleadoCalendarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def generar_calendario(
    negocio_id: int,
    id_empleado: int,
    request: GenerarCalendarioRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _verificar_due_o_admin(db, current_user, negocio_id)

    # Validar que el empleado pertenezca al negocio
    empleado = db.query(Empleado).filter(Empleado.id_empleado == id_empleado).first()
    if not empleado or empleado.id_negocio != negocio_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado para este negocio")

    link = enviar_link_por_email(db, id_empleado, request.email)

    return EmpleadoCalendarioResponse(
        id_empleado=id_empleado,
        calendario_link=link,
        calendario_enviado_at=empleado.calendario_enviado_at,
    )


@router.post(
    "/{negocio_id}/empleados/{id_empleado}/revocar-calendario",
    response_model=EmpleadoCalendarioResponse,
)
def revocar_calendario(
    negocio_id: int,
    id_empleado: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _verificar_due_o_admin(db, current_user, negocio_id)

    empleado = db.query(Empleado).filter(Empleado.id_empleado == id_empleado).first()
    if not empleado or empleado.id_negocio != negocio_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado para este negocio")

    revocar_token(db, id_empleado)

    # Después de revocar, el link viejo ya no sirve; token nuevo se generará en la próxima generación
    return EmpleadoCalendarioResponse(
        id_empleado=id_empleado,
        calendario_link=None,
        calendario_enviado_at=empleado.calendario_enviado_at,
    )


@router.get(
    "/{negocio_id}/empleados/{id_empleado}/calendario-estado",
    response_model=EmpleadoCalendarioEstadoResponse,
)
def calendario_estado(
    negocio_id: int,
    id_empleado: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _verificar_due_o_admin(db, current_user, negocio_id)

    empleado = db.query(Empleado).filter(Empleado.id_empleado == id_empleado).first()
    if not empleado or empleado.id_negocio != negocio_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado para este negocio")

    return EmpleadoCalendarioEstadoResponse(
        id_empleado=id_empleado,
        estado=obtener_estado_calendario(db, id_empleado),
        calendario_enviado_at=empleado.calendario_enviado_at,
    )


# --- Endpoint público: feed .ics ---

from fastapi import Response


router_publico = APIRouter(tags=["Empleados Calendario"])


@router_publico.get(
    "/empleados/{token}/calendario.ics", include_in_schema=False
)
def feed_calendario(
    token: str,
    db: Session = Depends(get_db),
):
    """Feed iCal público, protegido solo por el token (sin auth de sesión)."""
    try:
        contenido = generar_ics(db, token)
    except HTTPException:
        raise
    return Response(
        content=contenido,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="calendario.ics"'},
    )