from datetime import UTC, datetime, timedelta

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.estados_turno import (
    CANCELADO,
    CONFIRMADO,
    validar_transicion,
)
from app.models.cliente import Cliente
from app.models.empleado import Empleado
from app.models.horarios_negocio import HorarioNegocio
from app.models.negocio import Negocio
from app.models.servicio import Servicio
from app.models.turnos import Turno
from app.schemas.appointment_schema import CambiarEstadoTurno, TurnoActualizar, TurnoCrear
from app.services.email_service import send_booking_confirmation_email, send_cancellation_email


SOLAPAMIENTO_DETALLE = "El empleado ya tiene un turno en ese horario"


def listar_turnos(db: Session):
    return db.query(Turno).all()


def obtener_turno_por_id(db: Session, turno_id: int):
    return db.query(Turno).filter(Turno.id_turno == turno_id).first()


def obtener_servicio_del_negocio(db: Session, id_servicio: int, id_negocio: int):
    servicio = (
        db.query(Servicio)
        .join(Negocio, Negocio.id_negocio == Servicio.id_negocio)
        .filter(
            Servicio.id_servicio == id_servicio,
            Servicio.id_negocio == id_negocio,
            Servicio.activo.is_(True),
            Negocio.activo.is_(True),
        )
        .first()
    )

    if not servicio:
        raise HTTPException(
            status_code=404,
            detail="Servicio no encontrado para el negocio indicado o negocio inactivo",
        )

    return servicio


def validar_empleado_del_negocio(
    db: Session,
    id_negocio: int,
    id_empleado: int | None,
):
    if id_empleado is None:
        return

    empleado = db.query(Empleado).filter(
        Empleado.id_empleado == id_empleado,
        Empleado.id_negocio == id_negocio,
        Empleado.activo.is_(True),
    ).first()

    if not empleado:
        raise HTTPException(
            status_code=400,
            detail="Empleado no encontrado para el negocio indicado",
        )


def validar_turno_dentro_del_horario(
    db: Session,
    id_negocio: int,
    inicio: datetime,
    fin: datetime,
):
    horarios = db.query(HorarioNegocio).filter(
        HorarioNegocio.id_negocio == id_negocio
    ).all()

    if not horarios:
        return

    dias_semana_validos = {inicio.weekday(), inicio.isoweekday()}
    hora_inicio = inicio.time()
    hora_fin = fin.time()

    for horario in horarios:
        if horario.dia_semana not in dias_semana_validos:
            continue

        apertura = horario.hora_apertura
        cierre = horario.hora_cierre
        cruza_medianoche = cierre <= apertura

        if cruza_medianoche:
            hora_en_rango = lambda t: t >= apertura or t <= cierre
            if hora_en_rango(hora_inicio) and hora_en_rango(hora_fin):
                return
        else:
            if apertura <= hora_inicio and hora_fin <= cierre:
                return

    raise HTTPException(
        status_code=400,
        detail="El turno está fuera del horario de atención del negocio",
    )


def validar_rango_horario(inicio: datetime, fin: datetime | None):
    if fin is not None and fin <= inicio:
        raise HTTPException(
            status_code=400,
            detail="La fecha_hora_fin debe ser mayor que la fecha_hora_inicio",
        )


def hay_superposicion(
    db: Session,
    id_negocio: int,
    id_empleado: int | None,
    inicio: datetime,
    fin: datetime | None,
    excluir_turno_id: int | None = None,
):
    if fin is None:
        return False

    query = db.query(Turno).filter(
        Turno.id_negocio == id_negocio,
        Turno.fecha_hora_inicio < fin,
        Turno.fecha_hora_fin > inicio,
    )

    if id_empleado is not None:
        query = query.filter(Turno.id_empleado == id_empleado)

    if excluir_turno_id is not None:
        query = query.filter(Turno.id_turno != excluir_turno_id)

    return query.first() is not None


def _resolver_fecha_hora_fin(
    db: Session,
    id_servicio: int,
    id_negocio: int,
    fecha_hora_inicio: datetime,
    fecha_hora_fin: datetime | None = None,
) -> datetime:
    if fecha_hora_fin is not None:
        return fecha_hora_fin

    servicio = obtener_servicio_del_negocio(
        db=db,
        id_servicio=id_servicio,
        id_negocio=id_negocio,
    )
    return fecha_hora_inicio + timedelta(minutes=servicio.duracion_min)


def _resolver_estado_inicial(_servicio: Servicio) -> int:
    return CONFIRMADO


def _lanzar_error_integridad(e: IntegrityError) -> None:
    error_text = str(e.orig)

    if "ex_turno_no_solapa_por_empleado" in error_text:
        raise HTTPException(
            status_code=409,
            detail=SOLAPAMIENTO_DETALLE,
        ) from e

    raise HTTPException(
        status_code=400,
        detail=f"Error de integridad en la base de datos: {error_text}",
    ) from e


def crear_turno(db: Session, turno: TurnoCrear, background_tasks: BackgroundTasks):
    servicio = obtener_servicio_del_negocio(
        db=db,
        id_servicio=turno.id_servicio,
        id_negocio=turno.id_negocio,
    )

    fecha_hora_fin = _resolver_fecha_hora_fin(
        db=db,
        id_servicio=turno.id_servicio,
        id_negocio=turno.id_negocio,
        fecha_hora_inicio=turno.fecha_hora_inicio,
    )

    validar_rango_horario(turno.fecha_hora_inicio, fecha_hora_fin)
    validar_empleado_del_negocio(
        db=db,
        id_negocio=turno.id_negocio,
        id_empleado=turno.id_empleado,
    )
    validar_turno_dentro_del_horario(
        db=db,
        id_negocio=turno.id_negocio,
        inicio=turno.fecha_hora_inicio,
        fin=fecha_hora_fin,
    )

    if hay_superposicion(
        db=db,
        id_negocio=turno.id_negocio,
        id_empleado=turno.id_empleado,
        inicio=turno.fecha_hora_inicio,
        fin=fecha_hora_fin,
    ):
        raise HTTPException(
            status_code=409,
            detail=SOLAPAMIENTO_DETALLE,
        )

    # Buscamos los datos del cliente para WhatsApp ANTES de crear el turno
    cliente = db.query(Cliente).filter(Cliente.id_cliente == turno.id_cliente).first()
    if not cliente:
        raise HTTPException(
            status_code=404,  # Cambiado a 404 estándar de HTTP para Not Found
            detail="El cliente especificado no existe."
        )

    ahora = datetime.now(UTC)
    id_estado_inicial = _resolver_estado_inicial(servicio)

    nuevo_turno = Turno(
        id_negocio=turno.id_negocio,
        id_cliente=turno.id_cliente,
        id_servicio=turno.id_servicio,
        id_estado=id_estado_inicial,
        id_empleado=turno.id_empleado,
        fecha_hora_inicio=turno.fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        rechazado_motivo=None,
        created_at=ahora,
        updated_at=ahora,
    )

    try:
        db.add(nuevo_turno)
        db.commit()
        db.refresh(nuevo_turno)

        # Email de confirmación en background — no bloquea la respuesta 201
        if cliente.email:
            fecha_str = turno.fecha_hora_inicio.strftime("%d/%m/%Y")
            hora_str = turno.fecha_hora_inicio.strftime("%H:%M")
            nombre_negocio = servicio.negocio.nombre if hasattr(servicio, "negocio") else "TurnoGo"
            nombre_empleado = None
            if turno.id_empleado:
                emp = db.query(Empleado).filter(
                    Empleado.id_empleado == turno.id_empleado
                ).first()
                if emp:
                    nombre_empleado = f"{emp.nombre} {emp.apellido}".strip()

            background_tasks.add_task(
                send_booking_confirmation_email,
                email=cliente.email,
                id_turno=nuevo_turno.id_turno,
                nombre_negocio=nombre_negocio,
                nombre_servicio=servicio.nombre_servicio,
                nombre_empleado=nombre_empleado,
                fecha=fecha_str,
                hora=hora_str,
                direccion=servicio.negocio.direccion if hasattr(servicio, "negocio") else None,
                telefono_negocio=servicio.negocio.telefono if hasattr(servicio, "negocio") else None,
            )

        return nuevo_turno

    except IntegrityError as e:
        db.rollback()
        _lanzar_error_integridad(e)


def actualizar_turno(db: Session, turno_id: int, datos: TurnoActualizar):
    turno_db = db.query(Turno).filter(Turno.id_turno == turno_id).first()

    if not turno_db:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    nuevo_id_negocio = (
        datos.id_negocio if datos.id_negocio is not None else turno_db.id_negocio
    )
    nuevo_id_servicio = (
        datos.id_servicio if datos.id_servicio is not None else turno_db.id_servicio
    )
    nuevo_id_empleado = (
        datos.id_empleado if datos.id_empleado is not None else turno_db.id_empleado
    )
    nueva_fecha_inicio = (
        datos.fecha_hora_inicio
        if datos.fecha_hora_inicio is not None
        else turno_db.fecha_hora_inicio
    )

    servicio = obtener_servicio_del_negocio(
        db=db,
        id_servicio=nuevo_id_servicio,
        id_negocio=nuevo_id_negocio,
    )

    recalcular_fin = (
        datos.id_servicio is not None
        or datos.id_negocio is not None
        or datos.fecha_hora_inicio is not None
    )

    nueva_fecha_fin = (
        _resolver_fecha_hora_fin(
            db=db,
            id_servicio=nuevo_id_servicio,
            id_negocio=nuevo_id_negocio,
            fecha_hora_inicio=nueva_fecha_inicio,
            fecha_hora_fin=datos.fecha_hora_fin,
        )
        if recalcular_fin or datos.fecha_hora_fin is not None
        else turno_db.fecha_hora_fin
    )

    validar_rango_horario(nueva_fecha_inicio, nueva_fecha_fin)
    validar_empleado_del_negocio(
        db=db,
        id_negocio=nuevo_id_negocio,
        id_empleado=nuevo_id_empleado,
    )
    validar_turno_dentro_del_horario(
        db=db,
        id_negocio=nuevo_id_negocio,
        inicio=nueva_fecha_inicio,
        fin=nueva_fecha_fin,
    )
    if hay_superposicion(
        db=db,
        id_negocio=nuevo_id_negocio,
        id_empleado=nuevo_id_empleado,
        inicio=nueva_fecha_inicio,
        fin=nueva_fecha_fin,
        excluir_turno_id=turno_id,
    ):
        raise HTTPException(
            status_code=409,
            detail=SOLAPAMIENTO_DETALLE,
        )

    turno_db.id_negocio = nuevo_id_negocio
    turno_db.id_cliente = (
        datos.id_cliente if datos.id_cliente is not None else turno_db.id_cliente
    )
    turno_db.id_servicio = nuevo_id_servicio
    turno_db.id_empleado = nuevo_id_empleado
    turno_db.fecha_hora_inicio = nueva_fecha_inicio
    turno_db.fecha_hora_fin = nueva_fecha_fin

    if datos.id_estado is not None:
        if not validar_transicion(turno_db.id_estado, datos.id_estado):
            raise HTTPException(
                status_code=400,
                detail=f"No se puede pasar del estado {turno_db.id_estado} al {datos.id_estado}",
            )
        turno_db.id_estado = datos.id_estado

    if datos.rechazado_motivo is not None:
        turno_db.rechazado_motivo = datos.rechazado_motivo

    turno_db.updated_at = datetime.now(UTC)

    try:
        db.commit()
        db.refresh(turno_db)
        return turno_db

    except IntegrityError as e:
        db.rollback()
        _lanzar_error_integridad(e)


def borrar_turno(db: Session, turno_id: int):
    turno_db = db.query(Turno).filter(Turno.id_turno == turno_id).first()

    if not turno_db:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    try:
        db.delete(turno_db)
        db.commit()
        return turno_db

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar el turno: {str(e)}", )


def listar_turnos_por_negocio_y_rango(
    db: Session,
    id_negocio: int,
    desde: datetime,
    hasta: datetime,
    id_empleado: int | None = None,
):
    query = db.query(Turno).filter(
        Turno.id_negocio == id_negocio,
        Turno.fecha_hora_inicio < hasta,
        Turno.fecha_hora_fin > desde,
    )

    if id_empleado is not None:
        query = query.filter(Turno.id_empleado == id_empleado)

    return query.order_by(Turno.fecha_hora_inicio.asc()).all()


def cambiar_estado_turno(
    db: Session,
    turno_id: int,
    datos: CambiarEstadoTurno,
    id_negocio: int,
    background_tasks: BackgroundTasks,
):
    """Change the status of a turno with full validation.

    The caller must ensure *id_negocio* belongs to the authenticated owner.
    """
    turno_db = db.query(Turno).filter(Turno.id_turno == turno_id).first()

    if not turno_db:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    if turno_db.id_negocio != id_negocio:
        raise HTTPException(
            status_code=403,
            detail="Este turno no pertenece a tu negocio",
        )

    if not validar_transicion(turno_db.id_estado, datos.id_estado):
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede cambiar del estado {turno_db.id_estado} "
                f"al estado {datos.id_estado}"
            ),
        )

    es_cancelacion = datos.id_estado == CANCELADO and turno_db.id_estado != CANCELADO
    cliente_email = None
    nombre_negocio = None
    nombre_servicio = None
    fecha_str = None
    hora_str = None

    if es_cancelacion and turno_db.cliente and turno_db.cliente.email:
        cliente_email = turno_db.cliente.email
        nombre_negocio = turno_db.negocio.nombre if turno_db.negocio else "TurnoGo"
        nombre_servicio = turno_db.servicio.nombre_servicio if turno_db.servicio else "Servicio"
        fecha_str = turno_db.fecha_hora_inicio.strftime("%d/%m/%Y")
        hora_str = turno_db.fecha_hora_inicio.strftime("%H:%M")

    turno_db.id_estado = datos.id_estado

    if datos.rechazado_motivo is not None:
        turno_db.rechazado_motivo = datos.rechazado_motivo

    turno_db.updated_at = datetime.now(UTC)

    try:
        db.commit()
        db.refresh(turno_db)

        if es_cancelacion and cliente_email and datos.rechazado_motivo:
            background_tasks.add_task(
                send_cancellation_email,
                email=cliente_email,
                id_turno=turno_db.id_turno,
                nombre_negocio=nombre_negocio,
                nombre_servicio=nombre_servicio,
                fecha=fecha_str,
                hora=hora_str,
                motivo=datos.rechazado_motivo,
            )

        return turno_db

    except IntegrityError as e:
        db.rollback()
        _lanzar_error_integridad(e)
