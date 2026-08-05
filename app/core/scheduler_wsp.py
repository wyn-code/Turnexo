"""
Scheduler de recordatorios.

Solo envía recordatorios a negocios cuya suscripción activa incluya la
feature correspondiente (recordatorio_email / recordatorio_whatsapp).

NOTA: el job no se registra en main.py todavía. Para activarlo, llamar a
start_scheduler() en el arranque de la app y conectar el envío real
(whatsapp_service) en verificar_y_enviar_recordatorios.
"""
from datetime import datetime, timedelta

from app.core.dependencies import get_db
from app.models.turnos import Turno
from app.services.plan_service import negocio_tiene_funcion


def obtener_turnos_para_recordatorio(db, feature_key: str = "recordatorio_email") -> list[Turno]:
    """Turnos del próximo día-hora que aún no fueron notificados, solo de
    negocios con la feature de recordatorios activa (VIP)."""
    manana = datetime.now() + timedelta(days=1)
    rango_inicio = manana.replace(minute=0, second=0, microsecond=0)
    rango_fin = rango_inicio + timedelta(hours=1)

    turnos = (
        db.query(Turno)
        .filter(
            Turno.fecha_hora_inicio >= rango_inicio,
            Turno.fecha_hora_inicio < rango_fin,
            Turno.recordatorio_enviado == False,  # noqa: E712
        )
        .all()
    )

    return [
        turno
        for turno in turnos
        if negocio_tiene_funcion(turno.id_negocio, feature_key, db)
    ]


def verificar_y_enviar_recordatorios() -> None:
    """Job periódico: marca como enviado los recordatorios de turnos VIP."""
    db = next(get_db())
    try:
        turnos = obtener_turnos_para_recordatorio(db)
        for turno in turnos:
            # TODO: conectar el envío real (whatsapp_service.enviar_whatsapp o
            # email_service) antes de marcar como enviado.
            turno.recordatorio_enviado = True
        db.commit()
    finally:
        db.close()


def start_scheduler() -> None:
    """Registra el job periódico (por hora)."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(verificar_y_enviar_recordatorios, "interval", hours=1)
    scheduler.start()
