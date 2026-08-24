"""Servicios para generar y gestionar calendarios iCal de empleados."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import secrets

from fastapi import HTTPException
from icalendar import Calendar, Event

from app.core.estados_turno import CANCELADO
from app.models.empleado import Empleado
from app.models.turnos import Turno
from app.services.email_service import send_calendario_email

from app.core.config import BACKEND_URL


ZONA = ZoneInfo("America/Argentina/Buenos_Aires")


def obtener_o_crear_token(db, id_empleado: int) -> str:
    """Devuelve el token activo del empleado o crea uno nuevo."""

    empleado = (
        db.query(Empleado)
        .filter(Empleado.id_empleado == id_empleado)
        .first()
    )

    if not empleado:
        raise HTTPException(
            status_code=404,
            detail="Empleado no encontrado",
        )

    # Si ya tiene un token activo, reutilizarlo.
    if (
        empleado.calendario_token
        and empleado.calendario_token_revoked_at is None
    ):
        return empleado.calendario_token

    # Generar nuevo token.
    nuevo_token = secrets.token_urlsafe(32)

    empleado.calendario_token = nuevo_token
    empleado.calendario_token_revoked_at = None
    empleado.calendario_enviado_at = None

    db.commit()
    db.refresh(empleado)

    return nuevo_token


def obtener_estado_calendario(db, id_empleado: int) -> str:
    """Devuelve el estado del calendario del empleado.

    - "sin_calendario": nunca se generó un token.
    - "activo": tiene un token vigente (no revocado).
    - "revocado": su último token fue revocado.
    """

    empleado = (
        db.query(Empleado)
        .filter(Empleado.id_empleado == id_empleado)
        .first()
    )

    if not empleado:
        raise HTTPException(
            status_code=404,
            detail="Empleado no encontrado",
        )

    if not empleado.calendario_token:
        return "sin_calendario"

    if empleado.calendario_token_revoked_at is not None:
        return "revocado"

    return "activo"


def revocar_token(db, id_empleado: int):
    """Revoca el token actual del empleado."""

    empleado = (
        db.query(Empleado)
        .filter(Empleado.id_empleado == id_empleado)
        .first()
    )

    if not empleado:
        raise HTTPException(
            status_code=404,
            detail="Empleado no encontrado",
        )

    if (
        not empleado.calendario_token
        or empleado.calendario_token_revoked_at is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="El empleado no tiene un token activo para revocar",
        )

    empleado.calendario_token_revoked_at = datetime.now(UTC)

    db.commit()
    db.refresh(empleado)


def generar_ics(db, token: str) -> bytes:
    """Genera el feed iCal del empleado asociado al token."""

    empleado = (
        db.query(Empleado)
        .filter(
            Empleado.calendario_token == token,
            Empleado.calendario_token_revoked_at.is_(None),
        )
        .first()
    )

    if not empleado:
        raise HTTPException(
            status_code=404,
            detail="Link de calendario inválido o revocado",
        )

    ahora = datetime.now(UTC)

    turnos = (
        db.query(Turno)
        .filter(
            Turno.id_empleado == empleado.id_empleado,
            Turno.fecha_hora_inicio >= ahora,
        )
        .order_by(Turno.fecha_hora_inicio.asc())
        .all()
    )

    cal = Calendar()

    cal.add("prodid", "-//TurnoGo//Calendario de turnos//ES")
    cal.add("version", "2.0")
    cal.add(
        "x-wr-calname",
        f"TurnoGo - {empleado.nombre} {empleado.apellido}",
    )
    cal.add(
        "x-wr-timezone",
        "America/Argentina/Buenos_Aires",
    )

    for turno in turnos:
        servicio = turno.servicio

        if not servicio:
            continue

        inicio = _a_zonificado(turno.fecha_hora_inicio)

        if turno.fecha_hora_fin:
            fin = _a_zonificado(turno.fecha_hora_fin)

        elif servicio.duracion_min:
            fin = inicio + timedelta(
                minutes=servicio.duracion_min
            )

        else:
            fin = inicio

        event = Event()

        event.add(
            "uid",
            f"turno-{turno.id_turno}@turnogo.com",
        )

        event.add(
            "summary",
            servicio.nombre_servicio,
        )

        event.add(
            "location",
            turno.negocio.direccion,
        )

        event.add("dtstart", inicio)
        event.add("dtend", fin)

        # Marcar como cancelado en Google Calendar
        # si el turno fue cancelado.
        if turno.id_estado == CANCELADO:
            event.add("status", "CANCELLED")

        cal.add_component(event)

    return cal.to_ical()


def _a_zonificado(dt: datetime) -> datetime:
    """
    Convierte un datetime a la zona
    America/Argentina/Buenos_Aires.

    Si el datetime es naive, se interpreta como UTC.
    """

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(ZONA)


def enviar_link_por_email(
    db,
    id_empleado: int,
    email: str,
):
    """Genera el token, envía el link por email
    y actualiza la fecha de envío.
    """

    # Primero obtenemos el empleado.
    empleado = (
        db.query(Empleado)
        .filter(Empleado.id_empleado == id_empleado)
        .first()
    )

    if not empleado:
        raise HTTPException(
            status_code=404,
            detail="Empleado no encontrado",
        )

    # Obtener o crear token.
    token = obtener_o_crear_token(
        db,
        id_empleado,
    )

    link = (
        f"{BACKEND_URL.rstrip('/')}"
        f"/api/empleados/{token}/calendario.ics"
    )

    nombre_empleado = (
        f"{empleado.nombre} {empleado.apellido}"
    ).strip()

    send_calendario_email(
        email=email,
        link=link,
        nombre_empleado=nombre_empleado,
    )

    empleado.calendario_enviado_at = datetime.now(UTC)

    db.commit()
    db.refresh(empleado)

    return link
