# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Reglas de negocio puras RN-01..RN-14 y RF-09..RF-13."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.entities import Quadrant, TestObjectSpec, Validation, match_test_object
from app.domain.errors import (
    InvalidReportTypeError,
    OutsideRegisteredQuadrantError,
    ReportTypeMismatchError,
)

ALLOWED_REPORT_TYPES = ("movimiento", "brillo", "limpio")
ALLOWED_QUADRANT_STATES = ("pendiente", "confirmado", "descartado")
CONFIRMATION_VOTES_REQUIRED = 3
QUADRANT_MATCH_TOLERANCE_DEG = 0.5


def ensure_registered_quadrant(ra: float, dec: float) -> TestObjectSpec:
    """Rechaza coordenadas fuera de los cuadrantes registrados (RF-01, RN-10)."""
    matched = match_test_object(ra, dec, tolerance_deg=QUADRANT_MATCH_TOLERANCE_DEG)
    if matched is None:
        raise OutsideRegisteredQuadrantError(
            f"Coordenadas RA={ra:.4f}, Dec={dec:+.4f} fuera de los cuadrantes registrados. "
            "Solo se sirven los cuadrantes de la cola fija (RF-05)."
        )
    return matched


def validate_report_type(cuadrante: Quadrant, tipo: str) -> None:
    """Valida RN-02, RN-03 y RF-11 antes de guardar un reporte."""
    normalized = (tipo or "").strip().lower()
    if normalized not in ALLOWED_REPORT_TYPES:
        raise InvalidReportTypeError(
            f"Tipo de reporte invalido '{tipo}'. Valores permitidos: {', '.join(ALLOWED_REPORT_TYPES)}."
        )

    if normalized == "limpio":
        return

    if cuadrante.tipo_prueba and normalized != cuadrante.tipo_prueba:
        raise ReportTypeMismatchError(
            f"El cuadrante '{cuadrante.nombre}' pertenece al grupo '{cuadrante.tipo_prueba}'; "
            f"no se permite reportar '{normalized}' (RN-02/RN-03)."
        )


def confirm_report(votos_o_validaciones: int | Iterable[Validation]) -> bool:
    """Un reporte se confirma solo con >= 3 validaciones coincide=true (RF-12, RN-08)."""
    if isinstance(votos_o_validaciones, int) and not isinstance(votos_o_validaciones, bool):
        return votos_o_validaciones >= CONFIRMATION_VOTES_REQUIRED

    matching = sum(1 for v in votos_o_validaciones if v.coincide)
    return matching >= CONFIRMATION_VOTES_REQUIRED


def determine_quadrant_state_after_validation(
    current_state: str, report_confirmed: bool
) -> str:
    """RN-06: un cuadrante pasa a 'confirmado' solo cuando uno de sus reportes se confirma."""
    if report_confirmed:
        return "confirmado"
    return current_state


def classify_candidate(
    displacement_px: float,
    brightness_delta: float,
    slow_threshold_px: float = 2.5,
    motion_threshold_px: float = 0.8,
) -> tuple[str, str]:
    """Clasifica un candidato de resta |B - A| y genera explicacion legible (RF-09)."""
    if displacement_px >= slow_threshold_px:
        return (
            "movimiento",
            (
                f"Desplazamiento dipolar de {displacement_px:.1f} px entre Epoca A y B "
                f"con variacion delta={brightness_delta:.2f} sobre el umbral (movimiento propio rapido)"
            ),
        )
    if displacement_px >= motion_threshold_px:
        return (
            "lento",
            (
                f"Desplazamiento corto de {displacement_px:.1f} px entre Epoca A y B "
                f"con variacion delta={brightness_delta:.2f} sobre el umbral "
                f"(candidato de movimiento lento tipo Planet X)"
            ),
        )
    return (
        "brillo",
        (
            f"Posicion fija (desplazamiento {displacement_px:.1f} px) con variacion "
            f"fotometrica delta={brightness_delta:.2f} sobre el umbral (cambio de brillo)"
        ),
    )


def ensure_simulated_vote_labelled(validation: Validation) -> dict[str, object]:
    """RF-13: todo voto simulado debe llevar es_simulado=true y etiqueta explicita."""
    etiqueta = "simulado" if validation.es_simulado else "real"
    return {
        "validacion_id": validation.id,
        "reporte_id": validation.reporte_id,
        "coincide": validation.coincide,
        "es_simulado": validation.es_simulado,
        "etiqueta": etiqueta,
    }
