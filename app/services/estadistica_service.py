from datetime import datetime, timedelta, UTC, date

from sqlalchemy import func, case, distinct, and_, extract, cast, Date
from sqlalchemy.orm import Session

from app.core.estados_turno import (
    PENDIENTE, CONFIRMADO, COMPLETADO, CANCELADO, NO_ASISTIO,
    ATENDIDO_STATES,
)
from app.models.turnos import Turno
from app.models.servicio import Servicio
from app.models.empleado import Empleado
from app.models.cliente import Cliente


ACTIVE_STATES = [PENDIENTE, CONFIRMADO, *ATENDIDO_STATES]


def _date_range(date_start: date | None, date_end: date | None):
    today = datetime.now(UTC).date()
    start = date_start or today.replace(day=1)
    end = date_end or today
    return start, end


def _prev_period(start: date, end: date):
    duration = (end - start).days
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration)
    return prev_start, prev_end


def _month_ago(d: date) -> date:
    if d.month == 1:
        return d.replace(year=d.year - 1, month=12, day=d.day)
    return d.replace(month=d.month - 1, day=d.day)


def _year_ago(d: date) -> date:
    return d.replace(year=d.year - 1)


class StatisticsService:

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_statistics(
        self,
        business_id: int,
        date_start: date | None = None,
        date_end: date | None = None,
    ) -> dict:
        start, end = _date_range(date_start, date_end)
        prev_start, prev_end = _prev_period(start, end)
        today = datetime.now(UTC).date()

        all_turnos = self._get_turnos_range(business_id, start, end)
        prev_turnos = self._get_turnos_range(business_id, prev_start, prev_end)

        kpis = self._build_kpis(business_id, start, end, prev_start, prev_end, all_turnos)
        resumen = self._build_resumen(business_id, today, all_turnos, prev_turnos)
        clientes = self._build_clientes(business_id, start, end)
        servicios = self._build_servicios(business_id, start, end, all_turnos)
        ingresos = self._build_ingresos(business_id, start, end, all_turnos, prev_start, prev_end, prev_turnos)
        agenda = self._build_agenda(business_id, start, end, all_turnos)
        asistencia = self._build_asistencia(business_id, start, end, all_turnos)
        empleados = self._build_empleados(business_id, start, end, all_turnos)

        return {
            "kpis": kpis,
            "resumen": resumen,
            "clientes": clientes,
            "servicios": servicios,
            "ingresos": ingresos,
            "agenda": agenda,
            "asistencia": asistencia,
            "empleados": empleados,
        }

    # ------------------------------------------------------------------
    # Shared query helpers
    # ------------------------------------------------------------------

    def _get_turnos_range(self, bid: int, start: date, end: date):
        return (
            self.db.query(Turno)
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
            )
            .all()
        )

    def _count_active_in_range(self, bid: int, start: date, end: date) -> int:
        return (
            self.db.query(func.count(Turno.id_turno))
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .scalar()
            or 0
        )

    def _sum_revenue_in_range(self, bid: int, start: date, end: date) -> float:
        row = (
            self.db.query(func.coalesce(func.sum(Servicio.precio), 0.0))
            .join(Turno, Turno.id_servicio == Servicio.id_servicio)
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ATENDIDO_STATES),
            )
            .scalar()
        )
        return float(row)

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------

    def _build_kpis(self, bid, start, end, prev_start, prev_end, turnos):
        total_turnos = sum(1 for t in turnos if t.id_estado in ACTIVE_STATES)
        prev_total = self._count_active_in_range(bid, prev_start, prev_end)

        revenue = self._sum_revenue_in_range(bid, start, end)
        prev_revenue = self._sum_revenue_in_range(bid, prev_start, prev_end)

        clientes_activos = self._count_distinct_clients(bid, start, end)
        prev_clientes = self._count_distinct_clients(bid, prev_start, prev_end)

        servicio_mas_vendido = self._most_popular_service(bid, start, end)
        dia_mas_facturado = self._busiest_day_of_week(turnos)
        hora_mayor_demanda = self._peak_hour(turnos)
        ocupacion = self._calculate_occupancy(bid, start, end)

        return {
            "ingresoTotal": {
                "value": revenue,
                "delta": self._delta_pct(revenue, prev_revenue),
                "trend": "up" if revenue >= prev_revenue else "down",
            },
            "clientesActivos": {
                "value": clientes_activos,
                "delta": self._delta_pct(clientes_activos, prev_clientes),
                "trend": "up" if clientes_activos >= prev_clientes else "down",
            },
            "servicioMasVendido": servicio_mas_vendido,
            "diaMasFacturado": dia_mas_facturado,
            "horaMayorDemanda": hora_mayor_demanda,
            "ocupacionAgenda": {
                "value": ocupacion,
                "delta": None,
                "trend": None,
            },
        }

    # ------------------------------------------------------------------
    # Resumen
    # ------------------------------------------------------------------

    def _build_resumen(self, bid, today, turnos, prev_turnos):
        today_count = sum(
            1 for t in turnos
            if t.fecha_hora_inicio.date() == today and t.id_estado in ACTIVE_STATES
        )
        yesterday = today - timedelta(days=1)
        yesterday_count = self._count_active_day(bid, yesterday)

        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        last_week_start = week_start - timedelta(days=7)
        last_week_end = week_start - timedelta(days=1)

        week_count = sum(
            1 for t in turnos
            if week_start <= t.fecha_hora_inicio.date() <= week_end
            and t.id_estado in ACTIVE_STATES
        )
        prev_week_count = self._count_active_in_range(bid, last_week_start, last_week_end)

        month_count = sum(1 for t in turnos if t.id_estado in ACTIVE_STATES)
        prev_month_start, prev_month_end = _prev_period(today.replace(day=1), today)
        prev_month_count = self._count_active_in_range(bid, prev_month_start, prev_month_end)

        days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        turnos_por_dia = []
        for i in range(7):
            current_day = week_start + timedelta(days=i)
            previous_day = last_week_start + timedelta(days=i)
            actual = sum(
                1 for t in turnos
                if t.fecha_hora_inicio.date() == current_day and t.id_estado in ACTIVE_STATES
            )
            anterior = self._count_active_day(bid, previous_day)
            turnos_por_dia.append({
                "dia": days[i],
                "actual": actual,
                "anterior": anterior,
            })

        return {
            "turnosHoy": {
                "value": today_count,
                "delta": self._delta_count(today_count, yesterday_count),
                "trend": "up" if today_count >= yesterday_count else "down",
            },
            "turnosSemana": {
                "value": week_count,
                "delta": self._delta_count(week_count, prev_week_count),
                "trend": "up" if week_count >= prev_week_count else "down",
            },
            "turnosMes": {
                "value": month_count,
                "delta": self._delta_count(month_count, prev_month_count),
                "trend": "up" if month_count >= prev_month_count else "down",
            },
            "turnosPorDia": turnos_por_dia,
        }

    def _count_active_day(self, bid: int, d: date) -> int:
        return (
            self.db.query(func.count(Turno.id_turno))
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio) == d,
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .scalar()
            or 0
        )

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------

    def _build_clientes(self, bid, start, end):
        clientes_periodo = (
            self.db.query(func.count(func.distinct(Turno.id_cliente)))
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .scalar()
            or 0
        )

        prev_start, prev_end = _prev_period(start, end)
        prev_clientes = (
            self.db.query(func.count(func.distinct(Turno.id_cliente)))
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(prev_start, prev_end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .scalar()
            or 0
        )

        recurrentes_subq = (
            self.db.query(Turno.id_cliente)
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .group_by(Turno.id_cliente)
            .having(func.count(Turno.id_turno) > 1)
            .subquery()
        )
        recurrentes = (
            self.db.query(func.count()).select_from(recurrentes_subq).scalar() or 0
        )

        cutoff = start - timedelta(days=30)
        all_client_ids = (
            self.db.query(func.distinct(Turno.id_cliente))
            .filter(Turno.id_negocio == bid)
            .all()
        )
        recent_client_ids = (
            self.db.query(func.distinct(Turno.id_cliente))
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio) >= cutoff,
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .all()
        )
        recent_set = {r[0] for r in recent_client_ids}
        inactivos = sum(1 for (cid,) in all_client_ids if cid not in recent_set)

        top_visitas_rows = (
            self.db.query(
                Cliente.nombre,
                Cliente.apellido,
                func.count(Turno.id_turno).label("cnt"),
            )
            .join(Turno, Turno.id_cliente == Cliente.id_cliente)
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .group_by(Cliente.id_cliente)
            .order_by(func.count(Turno.id_turno).desc())
            .limit(5)
            .all()
        )

        top_cancel_rows = (
            self.db.query(
                Cliente.nombre,
                Cliente.apellido,
                func.count(Turno.id_turno).label("cnt"),
            )
            .join(Turno, Turno.id_cliente == Cliente.id_cliente)
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_([CANCELADO, NO_ASISTIO]),
            )
            .group_by(Cliente.id_cliente)
            .order_by(func.count(Turno.id_turno).desc())
            .limit(5)
            .all()
        )

        return {
            "nuevos": {
                "value": clientes_periodo,
                "delta": self._delta_count(clientes_periodo, prev_clientes),
                "trend": "up" if clientes_periodo >= prev_clientes else "down",
            },
            "recurrentes": {
                "value": recurrentes,
                "delta": None,
                "trend": None,
            },
            "inactivos": {
                "value": inactivos,
                "delta": None,
                "trend": None,
            },
            "topVisitas": [
                {"nombre": f"{n} {a}", "visitas": c, "cancelaciones": 0}
                for n, a, c in top_visitas_rows
            ],
            "topCancelaciones": [
                {"nombre": f"{n} {a}", "cancelaciones": c}
                for n, a, c in top_cancel_rows
            ],
        }

    def _count_distinct_clients(self, bid: int, start: date, end: date) -> int:
        return (
            self.db.query(func.count(func.distinct(Turno.id_cliente)))
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .scalar()
            or 0
        )

    # ------------------------------------------------------------------
    # Servicios
    # ------------------------------------------------------------------

    def _build_servicios(self, bid, start, end, turnos):
        svc_rows = (
            self.db.query(
                Servicio.nombre_servicio,
                Servicio.duracion_min,
                func.count(Turno.id_turno).label("cnt"),
                func.coalesce(
                    func.sum(
                        case(
                            (Turno.id_estado.in_(ATENDIDO_STATES), Servicio.precio),
                            else_=0,
                        )
                    ),
                    0.0,
                ).label("rev"),
            )
            .join(Turno, Turno.id_servicio == Servicio.id_servicio)
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .group_by(Servicio.id_servicio)
            .order_by(func.count(Turno.id_turno).desc())
            .all()
        )

        items = [
            {
                "nombre": n,
                "solicitados": c,
                "ingresos": float(r),
                "tiempo": d,
            }
            for n, d, c, r in svc_rows
        ]

        menos_solicitado = items[-1]["nombre"] if items else None

        return {
            "items": items,
            "menosSolicitado": menos_solicitado,
        }

    def _most_popular_service(self, bid: int, start: date, end: date) -> str:
        row = (
            self.db.query(Servicio.nombre_servicio)
            .join(Turno, Turno.id_servicio == Servicio.id_servicio)
            .filter(
                Turno.id_negocio == bid,
                func.date(Turno.fecha_hora_inicio).between(start, end),
                Turno.id_estado.in_(ACTIVE_STATES),
            )
            .group_by(Servicio.id_servicio)
            .order_by(func.count(Turno.id_turno).desc())
            .first()
        )
        return row[0] if row else "N/A"

    def _busiest_day_of_week(self, turnos) -> str:
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        day_counts: dict[int, int] = {}
        for t in turnos:
            if t.id_estado in ACTIVE_STATES:
                d = t.fecha_hora_inicio.weekday()
                day_counts[d] = day_counts.get(d, 0) + 1
        if not day_counts:
            return "N/A"
        return days[max(day_counts, key=day_counts.get)]

    def _peak_hour(self, turnos) -> str:
        hour_counts: dict[int, int] = {}
        for t in turnos:
            if t.id_estado in ACTIVE_STATES:
                h = t.fecha_hora_inicio.hour
                hour_counts[h] = hour_counts.get(h, 0) + 1
        if not hour_counts:
            return "N/A"
        peak = max(hour_counts, key=hour_counts.get)
        return f"{peak:02d}:00"

    def _calculate_occupancy(self, bid: int, start: date, end: date) -> int:
        total_slots = self._total_available_slots(bid, start, end)
        if total_slots <= 0:
            return 0
        active = self._count_active_in_range(bid, start, end)
        return min(int(round(active / total_slots * 100)), 100)

    # ------------------------------------------------------------------
    # Ingresos
    # ------------------------------------------------------------------

    def _build_ingresos(self, bid, start, end, turnos, prev_start, prev_end, prev_turnos):
        today = datetime.now(UTC).date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        diaria = self._sum_revenue_in_range(bid, today, today)
        prev_diaria = self._sum_revenue_in_range(bid, today - timedelta(days=1), today - timedelta(days=1))
        semanal = self._sum_revenue_in_range(bid, week_start, today)
        prev_semanal = self._sum_revenue_in_range(bid, week_start - timedelta(days=7), week_start - timedelta(days=1))
        mensual = self._sum_revenue_in_range(bid, month_start, today)
        prev_mensual = self._sum_revenue_in_range(bid, _month_ago(month_start), _month_ago(today))

        completed = [t for t in turnos if t.id_estado in ATENDIDO_STATES]
        ticket = mensual / len(completed) if completed else 0.0
        prev_completed_count = sum(1 for t in prev_turnos if t.id_estado in ATENDIDO_STATES)
        prev_ticket = prev_mensual / prev_completed_count if prev_completed_count else 0.0

        evolucion = self._monthly_income_evol(bid)

        return {
            "facturacionDiaria": {
                "value": diaria,
                "delta": self._delta_pct(diaria, prev_diaria),
                "trend": "up" if diaria >= prev_diaria else "down",
            },
            "facturacionSemanal": {
                "value": semanal,
                "delta": self._delta_pct(semanal, prev_semanal),
                "trend": "up" if semanal >= prev_semanal else "down",
            },
            "facturacionMensual": {
                "value": mensual,
                "delta": self._delta_pct(mensual, prev_mensual),
                "trend": "up" if mensual >= prev_mensual else "down",
            },
            "ticketPromedio": {
                "value": round(ticket, 2),
                "delta": self._delta_pct(ticket, prev_ticket),
                "trend": "up" if ticket >= prev_ticket else "down",
            },
            "evolucionMensual": evolucion,
        }

    def _monthly_income_evol(self, bid: int) -> list[dict]:
        today = datetime.now(UTC).date()
        rows = []
        months = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

        for i in range(5, -1, -1):
            ref = today.replace(day=1)
            for _ in range(i):
                ref = (ref - timedelta(days=1)).replace(day=1)
            month_start = ref
            if ref.month == 12:
                month_end = ref.replace(year=ref.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = ref.replace(month=ref.month + 1, day=1) - timedelta(days=1)

            rev = self._sum_revenue_in_range(bid, month_start, month_end)
            rows.append({
                "mes": months[month_start.month - 1],
                "ingresos": rev,
            })

        return rows

    # ------------------------------------------------------------------
    # Agenda
    # ------------------------------------------------------------------

    def _build_agenda(self, bid, start, end, turnos):
        active = [t for t in turnos if t.id_estado in ACTIVE_STATES]

        hour_counts: dict[int, int] = {}
        day_counts: dict[int, int] = {}
        for t in active:
            h = t.fecha_hora_inicio.hour
            hour_counts[h] = hour_counts.get(h, 0) + 1
            d = t.fecha_hora_inicio.weekday()
            day_counts[d] = day_counts.get(d, 0) + 1

        horarios_demanda = []
        for h in range(8, 21):
            horarios_demanda.append({
                "hora": f"{h:02d}:00",
                "turnos": hour_counts.get(h, 0),
            })

        horario_pico = "N/A"
        if hour_counts:
            peak_h = max(hour_counts, key=hour_counts.get)
            horario_pico = f"{peak_h:02d}:00"

        days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        dia_mas_turnos = "N/A"
        menor_ocupacion = "N/A"
        if day_counts:
            max_day_idx = max(day_counts, key=day_counts.get)
            min_day_idx = min(day_counts, key=day_counts.get)
            dia_mas_turnos = days[max_day_idx]
            menor_ocupacion = days[min_day_idx]

        total_slots = self._total_available_slots(bid, start, end)
        ocupacion = int(round(len(active) / total_slots * 100)) if total_slots > 0 else 0

        return {
            "horariosDemanda": horarios_demanda,
            "horarioPico": horario_pico,
            "diaMasTurnos": dia_mas_turnos,
            "menorOcupacion": menor_ocupacion,
            "ocupacionPorcentaje": min(ocupacion, 100),
        }

    def _total_available_slots(self, bid: int, start: date, end: date) -> int:
        from app.models.horarios_negocio import HorarioNegocio

        horarios = (
            self.db.query(HorarioNegocio)
            .filter(HorarioNegocio.id_negocio == bid)
            .all()
        )

        if not horarios:
            return 0

        day_minutes: dict[int, int] = {}
        for h in horarios:
            d = h.dia_semana
            minutes = 0
            if hasattr(h, "hora_apertura") and hasattr(h, "hora_cierre"):
                start_t = h.hora_apertura
                end_t = h.hora_cierre
                minutes = int((end_t.hour - start_t.hour) * 60 + (end_t.minute - start_t.minute))
            day_minutes[d] = day_minutes.get(d, 0) + minutes

        total = 0
        current = start
        while current <= end:
            dow = current.weekday()
            minutes = day_minutes.get(dow, 0)
            total += max(minutes // 30, 0)
            current += timedelta(days=1)

        return total

    # ------------------------------------------------------------------
    # Asistencia
    # ------------------------------------------------------------------

    def _build_asistencia(self, bid, start, end, turnos):
        completados = sum(1 for t in turnos if t.id_estado in ATENDIDO_STATES)
        cancelados = sum(1 for t in turnos if t.id_estado == CANCELADO)
        no_show = sum(1 for t in turnos if t.id_estado == NO_ASISTIO)
        pendientes = sum(1 for t in turnos if t.id_estado in [PENDIENTE, CONFIRMADO])
        total = len(turnos)
        tasa = int(round(completados / total * 100)) if total > 0 else 0

        return {
            "completados": completados,
            "cancelados": cancelados,
            "reprogramados": 0,
            "noShow": no_show,
            "distribucion": [
                {"name": "Completados", "value": completados},
                {"name": "Cancelados", "value": cancelados},
                {"name": "No Asistió", "value": no_show},
                {"name": "Pendientes", "value": pendientes},
            ],
            "tasaAsistencia": tasa,
            "totalTurnos": total,
        }

    # ------------------------------------------------------------------
    # Empleados
    # ------------------------------------------------------------------

    def _build_empleados(self, bid, start, end, turnos):
        emp_rows = (
            self.db.query(Empleado.id_empleado, Empleado.nombre, Empleado.apellido)
            .filter(Empleado.id_negocio == bid, Empleado.activo == True)
            .all()
        )

        results = []
        for eid, nombre, apellido in emp_rows:
            emp_turnos = [t for t in turnos if t.id_empleado == eid and t.id_estado in ACTIVE_STATES]
            emp_completed = [t for t in turnos if t.id_empleado == eid and t.id_estado in ATENDIDO_STATES]
            ingresos = sum(
                t.servicio.precio for t in emp_completed if t.servicio
            )
            total_emp = len(emp_turnos)
            ocupacion = int(round(total_emp / len(turnos) * 100)) if turnos else 0

            results.append({
                "nombre": f"{nombre} {apellido}",
                "turnos": total_emp,
                "ingresos": float(ingresos),
                "ocupacion": min(ocupacion, 100),
            })

        results.sort(key=lambda e: e["turnos"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Delta helpers
    # ------------------------------------------------------------------

    def _delta_pct(self, current: float, previous: float) -> str:
        if previous == 0:
            return "100%" if current > 0 else "0%"
        pct = ((current - previous) / previous) * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{round(pct, 1)}%"

    def _delta_count(self, current: int, previous: int) -> str:
        if previous == 0:
            return "+100%" if current > 0 else "0%"
        pct = ((current - previous) / previous) * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{round(pct, 1)}%"
