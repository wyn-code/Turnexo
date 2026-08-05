from datetime import UTC, datetime, timedelta

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.models.cliente import Cliente
from app.models.plan import Plan
from app.models.plan_feature import PlanFeature
from app.models.suscripcion import Suscripcion
from app.schemas.appointment_schema import TurnoCrear
from app.schemas.empleado_schema import EmpleadoCreate
from app.services.empleado_service import LIMITE_EMPLEADOS_FREE, crear_empleado
from app.services.negocio_service import obtener_negocio_por_slug
from app.services.turno_service import LIMITE_TURNOS_DIA_FREE, crear_turno
from app.core.scheduler_wsp import obtener_turnos_para_recordatorio


def _crear_plan_vip(db, feature_keys):
    plan = Plan(
        id_plan=999,
        nombre="VIP Test",
        precio=1000,
        duracion_dias=30,
        activo=True,
    )
    db.add(plan)
    db.flush()
    for key in feature_keys:
        db.add(PlanFeature(id_plan=plan.id_plan, feature_key=key))
    suscripcion = Suscripcion(
        id_negocio=1,
        id_plan=plan.id_plan,
        estado="activa",
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(suscripcion)
    db.commit()


def _crear_cliente(db, telefono):
    cliente = Cliente(
        telefono=telefono,
        nombre="Cliente",
        apellido="Test",
    )
    db.add(cliente)
    db.flush()
    return cliente


# ---------- EMPLEADOS ----------

def test_empleados_free_limite_3(db, seed_data):
    for i in range(2):
        empleado = crear_empleado(
            db,
            EmpleadoCreate(
                id_negocio=1,
                nombre=f"Extra{i}",
                apellido="Test",
                telefono=f"111{i}",
            ),
        )
        assert empleado.id_empleado

    with pytest.raises(HTTPException) as exc:
        crear_empleado(
            db,
            EmpleadoCreate(
                id_negocio=1,
                nombre="Sobrante",
                apellido="Test",
                telefono="999",
            ),
        )
    assert exc.value.status_code == 403
    assert str(LIMITE_EMPLEADOS_FREE) in exc.value.detail


def test_empleados_vip_sin_limite(db, seed_data):
    _crear_plan_vip(db, ["empleados_ilimitados"])

    for i in range(LIMITE_EMPLEADOS_FREE + 2):
        empleado = crear_empleado(
            db,
            EmpleadoCreate(
                id_negocio=1,
                nombre=f"Vip{i}",
                apellido="Test",
                telefono=f"222{i}",
            ),
        )
        assert empleado.id_empleado


# ---------- TURNOS ----------

_contador_cliente = 0


def _crear_turno(db, hora_inicio: datetime) -> None:
    global _contador_cliente
    _contador_cliente += 1
    _crear_cliente(db, telefono=f"333{_contador_cliente}")
    crear_turno(
        db,
        TurnoCrear(
            id_negocio=1,
            id_cliente=_cliente_ultimo(db),
            id_servicio=1,
            fecha_hora_inicio=hora_inicio,
            id_empleado=1,
        ),
        BackgroundTasks(),
    )


def _cliente_ultimo(db):
    return (
        db.query(Cliente).order_by(Cliente.id_cliente.desc()).first().id_cliente
    )


def test_turnos_free_limite_10_por_dia(db, seed_data):
    base = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    for i in range(LIMITE_TURNOS_DIA_FREE):
        _crear_turno(db, base + timedelta(minutes=i * 40))

    with pytest.raises(HTTPException) as exc:
        _crear_turno(db, base + timedelta(minutes=LIMITE_TURNOS_DIA_FREE * 40))
    assert exc.value.status_code == 403
    assert str(LIMITE_TURNOS_DIA_FREE) in exc.value.detail


def test_turnos_vip_sin_limite(db, seed_data):
    _crear_plan_vip(db, ["turnos_ilimitados"])

    base = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    for i in range(LIMITE_TURNOS_DIA_FREE + 2):
        _crear_turno(db, base + timedelta(minutes=i * 40))


# ---------- RECORDATORIOS (solo VIP) ----------

def test_recordatorios_solo_vip(db, seed_data):
    cliente = _crear_cliente(db, "4444")
    manana = (datetime.now() + timedelta(days=1)).replace(
        minute=30, second=0, microsecond=0
    )
    turno = TurnoCrear(
        id_negocio=1,
        id_cliente=cliente.id_cliente,
        id_servicio=1,
        fecha_hora_inicio=manana,
        id_empleado=1,
    )
    crear_turno(db, turno, BackgroundTasks())

    # Free: sin feature de recordatorio -> no aparece
    assert obtener_turnos_para_recordatorio(db, "recordatorio_email") == []

    # VIP: con la feature -> aparece
    _crear_plan_vip(db, ["recordatorio_email"])
    encontrados = obtener_turnos_para_recordatorio(db, "recordatorio_email")
    assert len(encontrados) == 1
    assert encontrados[0].id_turno == turno_guardado(db)


def turno_guardado(db):
    from app.models.turnos import Turno

    return db.query(Turno).first().id_turno


# ---------- MAPA (solo VIP) ----------

def test_mapa_gateado_por_funcion(db, seed_data):
    negocio = obtener_negocio_por_slug(db, "test-negocio")
    assert negocio.tiene_mapa is False

    _crear_plan_vip(db, ["mapa_ubicacion"])
    negocio = obtener_negocio_por_slug(db, "test-negocio")
    assert negocio.tiene_mapa is True
