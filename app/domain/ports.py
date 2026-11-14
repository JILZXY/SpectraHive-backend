# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Puertos (interfaces typing.Protocol) que implementa la capa de infraestructura."""

from __future__ import annotations

from typing import Protocol

from app.domain.entities import Candidate, Quadrant, Report, SpectralSignature, Validation
from app.domain.value_objects import Cutout, Epoch, Fov, Image, RaDec


class CutoutProvider(Protocol):
    """Obtiene cutouts de una coordenada y epoca (precalculados o fallback)."""

    def get_cutout(self, ra_dec: RaDec, fov: Fov, epoch: Epoch) -> Cutout: ...


class AlignmentService(Protocol):
    """Alinea dos imagenes astronomicas sin reproyeccion general (RN-09)."""

    def align(self, a: Image, b: Image) -> tuple[Image, Image, tuple[int, int]]: ...


class DiffProcessor(Protocol):
    """Calcula |B - A| normalizado (1-99), umbral, candidatos y renderiza PNG."""

    def compute_diff_and_render(
        self, a: Image, b: Image
    ) -> tuple[float, list[Candidate], bytes]: ...


class SpectralProvider(Protocol):
    """Entrega la firma espectral precalculada del ADN Cosmico (RF-14)."""

    def signature(self, objeto: str) -> SpectralSignature: ...

    def list_objects(self) -> list[str]: ...


class QuadrantRepository(Protocol):
    """Repositorio de la cola fija de cuadrantes."""

    def get(self, id_or_name: str) -> Quadrant | None: ...

    def list_queue(self) -> list[Quadrant]: ...

    def update_state(self, quadrant_id: str, new_state: str) -> None: ...


class ReportRepository(Protocol):
    """Repositorio transaccional de reportes y validaciones cruzadas."""

    def save(self, report: Report) -> Report: ...

    def get(self, reporte_id: str) -> Report | None: ...

    def validations_for(self, reporte_id: str) -> list[Validation]: ...

    def add_validation_and_check_confirmation(
        self, validation: Validation
    ) -> tuple[Validation, int, bool, str]: ...


class CutoutCache(Protocol):
    """Cache local o remota de cutouts."""

    def get(self, key: str) -> bytes | None: ...

    def set(self, key: str, value: bytes) -> None: ...
