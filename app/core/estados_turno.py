
PENDIENTE = 1
CONFIRMADO = 2
COMPLETADO = 3
CANCELADO = 4
NO_ASISTIO = 5
ASISTIO = 6

NOMBRE_ESTADO = {
    PENDIENTE: "PENDIENTE",
    CONFIRMADO: "CONFIRMADO",
    COMPLETADO: "COMPLETADO",
    CANCELADO: "CANCELADO",
    NO_ASISTIO: "NO_ASISTIO",
    ASISTIO: "ASISTIO",
}

# Transiciones válidas: estado_actual → [estados_finales_permitidos]
TRANSICIONES_PERMITIDAS: dict[int, list[int]] = {
    PENDIENTE: [CONFIRMADO, CANCELADO],
    # Un turno CONFIRMADO solo puede pasar a ASISTIO, CANCELADO o NO_ASISTIO.
    CONFIRMADO: [ASISTIO, CANCELADO, NO_ASISTIO],
}

# Estados que se consideran "atendido/completado" para métricas e ingresos.
# COMPLETADO se conserva por compatibilidad con turnos históricos.
ATENDIDO_STATES: list[int] = [COMPLETADO, ASISTIO]


def validar_transicion(estado_actual: int, nuevo_estado: int) -> bool:
    """Return True si la transición es permitida."""
    return nuevo_estado in TRANSICIONES_PERMITIDAS.get(estado_actual, [])
