# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Objetos de transferencia entre API y casos de uso."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities import Candidate


@dataclass(frozen=True)
class CutoutResult:
    """Salida de GetCutout."""

    ra: float
    dec: float
    fov: int
    epoca: str
    fuente: str
    imagen_base64: str
    png_bytes: bytes
    objeto: str | None = None


@dataclass(frozen=True)
class DiffResult:
    """Salida de ComputeDiff."""

    cuadrante_id: str
    epoca_a: str
    epoca_b: str
    umbral: float
    candidatos: list[Candidate]
    imagen_base64: str
    png_bytes: bytes
    fuente: str
    shift_aplicado: tuple[int, int]


@dataclass(frozen=True)
class ReportResult:
    """Salida de CreateReport."""

    reporte_id: str
    cuadrante_id: str
    estado: str
    tipo: str


@dataclass(frozen=True)
class ValidationResult:
    """Salida de ValidateReport."""

    validacion_id: str
    reporte_id: str
    coincide: bool
    es_simulado: bool
    etiqueta: str
    votos_coinciden: int
    confirmado: bool
    estado_cuadrante: str
